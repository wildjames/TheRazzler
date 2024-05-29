"""This scripts should create a bot that gets and stores incoming messages from
the signal server (use the signal API class provided).

Incoming messages are checked periodically, and added to a rabbitMQ queue for
processing by other components.

Outgoing messages are received from the rabbitMQ queue and sent to the signal
server.
"""

import asyncio
import json
from logging import getLogger
from typing import Any, Dict

import aio_pika
import redis
from utils.phonebook import PhoneBook
from utils.storage import (
    RedisCredentials,
    load_file_lock,
    load_phonebook,
)

from .signal_api import SignalAPI
from .signal_data_classes import IncomingMessage, SignalCredentials

logger = getLogger(__name__)


class SignalConsumer:
    """The consumer class handles checking for new messages, and placing them
    on the queue.
    """

    phonebook: PhoneBook
    api_client: SignalAPI
    signal_info: SignalCredentials
    redis_client: redis.Redis
    event_loop: asyncio.AbstractEventLoop
    rabbit_config: dict

    def __init__(
        self,
        signal_info: SignalCredentials,
        redis_config: RedisCredentials,
        rabbit_config: dict,
    ):
        logger.info("Initializing SignalConsumer...")
        self.api_client = SignalAPI(
            signal_info.signal_service, signal_info.phone_number
        )
        self.signal_info = signal_info
        self.rabbit_config = rabbit_config
        self.redis_client = redis.Redis(**redis_config.model_dump())

        # RabbitMQ connection
        self.connection = None

        # Set up the phonebook
        if load_phonebook() == PhoneBook():
            with load_file_lock("phonebook.json") as f:
                f.seek(0)
                f.write(PhoneBook().model_dump_json())
                f.truncate()

        logger.info("SignalConsumer initialized.")

    def __del__(self):
        self.stop()

    async def update_groups(self):
        """Update the groups in the phonebook.
        Fetches from signal a list of currently participating groups, and adds
        them to the phonebook."""
        groups = await self.api_client.get_groups()
        with load_file_lock("phonebook.json") as f:
            phonebook = PhoneBook(**json.load(f))
            for group in groups:
                logger.info(f"Adding group to phonebook: {group}")
                phonebook.add_group(group)
            pb_string = phonebook.model_dump_json()

            # Write the updated phonebook back to the file
            f.seek(0)
            f.write(pb_string)
            f.truncate()

    def get_rabbitmq_connection(self):
        return aio_pika.connect_robust(**self.rabbit_config)

    async def _init_mq(self):
        """Initialize RabbitMQ connection and declare the queue
        asynchronously."""
        logger.info("Initializing RabbitMQ connection...")
        self.connection = await self.get_rabbitmq_connection()

        async with self.connection:
            channel = await self.connection.channel()  # Get channel
            await channel.set_qos(prefetch_count=1)
            await channel.declare_queue("incoming_messages", durable=True)
        logger.info("Connected to RabbitMQ and declared the queues.")

    async def start(self):
        logger.info(
            f"Starting SignalConsumer for {self.signal_info.phone_number}..."
        )
        await self._init_mq()
        await self.update_groups()
        await self.listen()

    async def stop(self):
        await self.connection.close()
        logger.info("Connection closed. Stopped SignalConsumer")

    async def listen(self):
        """Check for new messages to add to the message queue."""
        async for raw_message in self.api_client.receive():
            message = json.loads(raw_message)

            logger.debug(f"Signal API yielded the message: {message}")
            # Add a queue item to process the incoming message
            await self._process_incoming(message)

    async def _publish_message(self, msg: IncomingMessage):
        """Serialize and publish messages to RabbitMQ."""
        logger.info(f"Publishing an incoming message to RabbitMQ: {msg}")
        serialized_message = msg.model_dump_json()

        # Reconnect if the connection is closed
        if self.connection.is_closed:
            self.connection = await self.get_rabbitmq_connection()

        async with self.connection as conn:
            async with conn.channel() as channel:
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=serialized_message.encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key="incoming_messages",
                )
                logger.info(
                    "Added message to the processing queue: Timestamp"
                    f" {msg.envelope.timestamp} from"
                    f" {msg.envelope.sourceNumber}"
                )

    async def _process_incoming(self, message: Dict[str, Any]):
        """Process incoming messages."""
        logger.debug("Processing incoming message")

        # Parse the json payload to an IncomingMessage object
        try:
            msg = IncomingMessage(**message)
        except Exception as e:
            logger.error(
                f"Error parsing incoming message: {e}. Message: {message}"
            )
            return
        logger.debug("Parsed incoming message payload")

        # We got a message, which may contain information about a contact
        # that we don't have yet.
        # First, check if the contact information is new to me
        phonebook = load_phonebook()
        is_updated = phonebook.update_contact(
            msg.envelope.sourceUuid,
            msg.envelope.sourceNumber,
            msg.envelope.sourceName,
        )
        if is_updated:
            # If it is, then get a lock on the file and update the phonebook
            # properly
            with load_file_lock("phonebook.json") as f:
                phonebook = PhoneBook(**json.load(f))
                phonebook.update_contact(
                    msg.envelope.sourceUuid,
                    msg.envelope.sourceNumber,
                    msg.envelope.sourceName,
                )

                # Write the updated phonebook back to the file
                f.seek(0)
                f.write(phonebook.model_dump_json())
                f.truncate()

            logger.info(f"Updated phonebook contact: {msg.envelope.source}")

        # DataMessages contain actual message content.
        if msg.envelope.dataMessage:
            logger.debug("Data message received")
            data = msg.envelope.dataMessage

            # If it has an attachement, we need to download it
            if data.attachments:
                logger.info("Message has attachments.")
                for attachment in data.attachments:
                    logger.info(f"Downloading attachment: {attachment.id}")
                    attachment_bytes = (
                        await self.api_client.download_attachment(
                            attachment.id
                        )
                    )
                    local_filename = f"attachments/{attachment.id}"
                    with load_file_lock(local_filename, "wb") as f:
                        f.write(attachment_bytes)
                    # convert the bytes to b64 for storage
                    attachment.data = local_filename
                    logger.debug(f"Downloaded attachment: {attachment.id}")

            # TODO: Parse mentions in the message body, into contact names.

            # Place the message in the message history list
            self.redis_client.lpush("message_history", msg.model_dump_json())
            # Ensure the message history cache doesn't grow too large
            self.redis_client.ltrim(
                "message_history", 0, self.signal_info.message_history_length
            )

        # Add the message to the processing queue
        await self._publish_message(msg)
