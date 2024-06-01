"""The Razzler brain listens to the RabbitMQ queue for incoming messages, and
decides how to respond to them. It then sends the responses back to the queue
in the outgoing_messages queue."""

import asyncio
import json
from logging import getLogger
from typing import List

import aio_pika
import redis
from signal_interface.dataclasses import (
    IncomingMessage,
    OutgoingReaction,
)
from utils.storage import RedisCredentials, load_file, file_lock

from .commands.base_command import CommandHandler
from .commands.registry import COMMAND_REGISTRY, COMMAND_PROCESSING_ORDER
from .dataclasses import RazzlerBrainConfig

logger = getLogger(__name__)


class RazzlerBrain:
    commands: List[CommandHandler]
    whitelist_file = "whitelisted_groups.json"

    def __init__(
        self,
        redis_config: RedisCredentials,
        rabbit_config: dict,
        brain_config: RazzlerBrainConfig,
    ):
        self.brain_config = brain_config
        self.rabbit_config = rabbit_config
        self.redis_client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
        )

        # Register the commands with the brain
        # The order of the commands is important, since some can apply to
        # similar messages. The first command in the priority order that can
        # handle a message will be the one to process it.
        self.commands = []
        for command in COMMAND_PROCESSING_ORDER:
            if command in self.brain_config.commands:
                logger.info(f"Registering command: {command}")
                # This is an instance of the command class.
                # If they have init arguments, they should be passed here.
                # TODO: Alter the config file to take commands with arguments
                # e.g. prompt filenames
                self.commands.append(COMMAND_REGISTRY[command]())

        # Check for any whitelisted groups
        whitelisted_groups = load_file(self.whitelist_file)
        if whitelisted_groups:
            whitelisted_groups = json.loads(whitelisted_groups)
        else:
            whitelisted_groups = []
            with file_lock(self.whitelist_file) as f:
                json.dump(whitelisted_groups, f)

        logger.info(
            "Starting the Razzler with the following groups whitelisted:"
            f" {whitelisted_groups}"
        )
        # If we have any, add them to the Redis set
        if whitelisted_groups:
            self.redis_client.sadd("whitelisted_groups", *whitelisted_groups)

    async def consume_messages(self):
        """Consume messages from RabbitMQ and process them."""
        logger.info("Consuming messages from RabbitMQ...")

        # Reopen the connection, if necessary
        if not self.connection or self.connection.is_closed:
            self.connection = await self.get_rabbitmq_connection()

        # Open a channel and consume incoming messages
        async with self.connection:
            self.channel = await self.connection.channel()
            queue = await self.channel.declare_queue(
                "incoming_messages", durable=True
            )
            await queue.consume(self._process_incoming_message)
            logger.info("Consuming messages...")
            await asyncio.Future()

    def get_rabbitmq_connection(self):
        return aio_pika.connect_robust(**self.rabbit_config)

    async def _init_mq(self):
        """Asynchronously initialize RabbitMQ connection and channel."""
        self.connection = await self.get_rabbitmq_connection()

        async with self.connection:
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=1)
            await self.channel.declare_queue("incoming_messages", durable=True)
            await self.channel.declare_queue("outgoing_messages", durable=True)

    async def start(self):
        """Start consuming messages from RabbitMQ."""
        logger.info("Starting RazzlerBrain...")
        await self._init_mq()
        await self.consume_messages()

    def stop(self):
        """Stop the RabbitMQ consumer."""
        if self.connection:
            self.connection.close()
            logger.info("RabbitMQ connection closed.")

    def __del__(self):
        self.stop()

    def replace_message_in_history(
        self,
        original_message: IncomingMessage,
        new_message: IncomingMessage,
    ):
        """Given an original message and a new message, replace the original
        message in the message history with the new message.

        Matches based on timestamp of the message."""

        logger.info(f"Replacing message with {new_message}")

        timestamp = original_message.envelope.timestamp
        chat = original_message.get_recipient()

        msg_cache = f"message_history:{chat}"

        # Get the index of the original message in the
        # message history
        length = self.redis_client.llen(msg_cache)
        logger.info(f"Message history length: {length}")

        for i in range(length):
            message_str = self.redis_client.lindex(msg_cache, i)
            message = json.loads(message_str)

            # If the message is of type IncomingMessage, instatiate it
            if "envelope" in message:
                message = IncomingMessage(**message)
            else:
                # If the message is not of type IncomingMessage, skip it
                continue

            # Try and parse the message for a timestamp
            fetched_timestamp = message.envelope.timestamp
            if fetched_timestamp == timestamp:
                logger.info(
                    "Found the original message - removing it "
                    "from the message history"
                )
                # Remove the original message from the message history
                self.redis_client.lrem(
                    msg_cache,
                    0,
                    message_str,
                )
                break
        else:
            # Default to the front of the list
            logger.info("Original message not found in the message history")
            i = 0

        # Push the new message into the message history
        length = self.redis_client.llen(msg_cache)

        # If the list is empty, push the new message to the front
        if length == 0:
            self.redis_client.lpush(
                msg_cache,
                new_message.model_dump_json(),
            )
            logger.info("Pushed new message into message history")
            return

        # If the list has changed since we started, and the index is now
        # out of bounds, push the new message to the end of the list
        if i >= length:
            self.redis_client.rpush(
                msg_cache,
                new_message.model_dump_json(),
            )
            logger.info("Pushed new message into message history")
            return

        # Otherwise, set the new message at the index of the original message
        self.redis_client.lset(
            msg_cache,
            i,
            new_message.model_dump_json(),
        )
        logger.info("Pushed new message into message history")

    async def acknowledge_message(
        self, message: IncomingMessage, emoji: str = "👍"
    ):
        """Just acknowledge the message by reacting to it"""
        # Publish a reaction to the message to acknowledge the whitelist
        reaction = OutgoingReaction(
            recipient=CommandHandler.get_recipient(message),
            reaction=emoji,
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )

        # Publish the outgoing message to the queue
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=reaction.model_dump_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="outgoing_messages",
        )

    async def is_group_whitelisted(self, message: IncomingMessage) -> bool:
        """Check if a group is whitelisted for processing. If a message is not
        from a group, it is whitelisted by default.

        Whitelist a group for processing.

        To whitelist a group, an admin has to send the following message in it:
            !whitelist
        """
        wl_key = "whitelisted_groups"

        logger.info("Checking if this group needs to be whitelisted...")
        # Check that the message is a group message
        try:
            gid = message.envelope.dataMessage.groupInfo.groupId
        except AttributeError:
            logger.info("Cannot whitelist group; message is not from a group")
            # All direct messages are whitelisted
            return True

        # Check that this message is from an admin
        if message.envelope.sourceNumber not in self.brain_config.admins:
            logger.info("Cannot whitelist group; message is not from an admin")
            return self.redis_client.sismember(wl_key, gid)

        # Check if the message content is the whitelist command
        if not message.envelope.dataMessage.message:
            logger.info("Message has no text content.")
            return self.redis_client.sismember(wl_key, gid)

        msg = message.envelope.dataMessage.message
        if msg not in ["!whitelist", "!blacklist"]:
            # This is a normal message.
            return self.redis_client.sismember(wl_key, gid)

        match msg:
            case "!whitelist":
                # Whitelist the group
                logger.info(f"Whitelisting group {gid}")
                self.redis_client.sadd(wl_key, gid)
                with file_lock(self.whitelist_file) as f:
                    whitelisted_groups: List[str] = json.load(f)
                    whitelisted_groups.append(gid)
                    f.seek(0)
                    json.dump(whitelisted_groups, f)
                    f.truncate()

            case "!blacklist":
                # Blacklist the group
                logger.info(f"Blacklisting group {gid}")
                self.redis_client.srem(wl_key, gid)
                with file_lock(self.whitelist_file) as f:
                    whitelisted_groups: List[str] = json.load(f)
                    whitelisted_groups.remove(gid)
                    f.seek(0)
                    json.dump(whitelisted_groups, f)
                    f.truncate()

            case _:
                raise ValueError(f"Invalid message content: {msg}")

        await self.acknowledge_message(message)
        return msg == "!whitelist"

    async def _process_incoming_message(
        self,
        message: aio_pika.IncomingMessage,
    ):
        """For an incoming message, parse the incoming message JSON string into
        an IncomingMessage object, then loop over the commands to see if any
        can handle the message. If a command can handle the message, run it.

        Note that all messages able to be handled by a command will be handled,
        so if a message *could* be handled by multiple commands, it will be.
        """

        # TODO: This is not ideal. As-is, I need to have logic in some commands
        # to check if a message that they *could* theoretically handle has been
        # handled by another command. However, I still any want them to run.
        #
        # For example, take the case where a message is replying to a message
        # that has an image in it, while they also address the razzler. We want
        # to trigger the "see_image" command to parse the image content, but we
        # ALSO want to trigger the response.
        #
        # However, take the case where they post an image, and request some
        # reply from the razzler. We want to use the image-embedded reply
        # generator, since that sees the image directly, but we DONT want the
        # plain text reply command to run, since then they'd get two replies
        # where only one knows what the image is, and we only wanted one anyway
        #
        # Can we make this more efficient? I'm not sure. I think we need to
        # keep the current structure, but we can make it more efficient by
        # having the commands return a flag that says "I handled this message"?
        # Trouble is, what if we want only *some* commands to be blocked?
        # Could build a list of commands that handled the message, and
        # have commands cross-reference that list before running?
        # That feels clunky too. I want them to be as modular as possible,
        # which ideally means they don't need to know about each other.
        # Perhaps the Razzler command registry can hold that information?
        # This method is called for each incoming message.
        # Here, we can assume the connection is open and the channel is
        # available, since it is called from the consume_messages method.

        logger.info("Processing incoming message...")
        async with message.process():

            # RabbitMQ messages are bytes, so we need to decode them
            message_data = json.loads(message.body.decode())
            # And parse into the IncomingMessage model
            msg = IncomingMessage(**message_data)
            logger.info(f"Received message: {msg}")

            # If the message is from a group, check that it's whitelisted
            if not await self.is_group_whitelisted(msg):
                gid = msg.envelope.dataMessage.groupInfo.groupId
                logger.info(f"Skipping message from group {gid}")
                return

            # Loop over commands. If a command can handle the message, run it.
            # Executes ALL commands able to handle a message, sequentially.
            for command in self.commands:
                if not command.can_handle(
                    msg, self.redis_client, self.brain_config
                ):
                    logger.debug(f"Skipping command {command}")
                    continue

                logger.info(f"Handling message with {command}")
                for response in command.handle(
                    msg, self.redis_client, self.brain_config
                ):
                    # If the command returns None, there's nothing to do.
                    # Go to the next response.
                    if response is None:
                        logger.debug("Command yielded None")
                        continue

                    logger.info(f"Command {command} produced message: {response}")

                    # In the specific case of the command yielding an incoming
                    # message, it is a replacement for the message that was
                    # processed. We need to remove the original message from
                    # the message history, if it's not been done already, then
                    # push the new message into its place
                    # NOTE: This is SLOW!
                    if isinstance(response, IncomingMessage):
                        self.replace_message_in_history(msg, response)

                        # We don't publish the incoming message to the queue
                        # so go to the next response
                        continue

                    # Publish the outgoing message to the queue
                    await self.channel.default_exchange.publish(
                        aio_pika.Message(
                            body=response.model_dump_json().encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        ),
                        routing_key="outgoing_messages",
                    )
