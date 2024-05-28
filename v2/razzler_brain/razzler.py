"""The Razzler brain listens to the RabbitMQ queue for incoming messages, and
decides how to respond to them. It then sends the responses back to the queue
in the outgoing_messages queue."""

import asyncio
import json
from logging import getLogger
from typing import List, Union

import aio_pika
import redis
from pydantic import BaseModel
from signal_interface.signal_data_classes import (
    IncomingMessage,
    OutgoingMessage,
    OutgoingReaction,
)
from utils.storage import RedisCredentials

from .commands.base_command import CommandHandler
from .commands.registry import COMMAND_REGISTRY

logger = getLogger(__name__)


class RazzlerBrainConfig(BaseModel):
    commands: List[str]


class RazzlerBrain:
    commands: List[CommandHandler]

    def __init__(
        self,
        redis_config: RedisCredentials,
        rabbit_config: dict,
        brain_config: RazzlerBrainConfig,
    ):
        self.rabbit_config = rabbit_config
        self.redis_client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
        )

        # Register the commands with the brain
        self.commands = []
        for command in brain_config.commands:
            logger.info(f"Registering command: {command}")
            self.commands.append(COMMAND_REGISTRY[command]())

    def __del__(self):
        self.stop()

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
        self.connection.close()
        logger.info("RabbitMQ connection closed.")

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

    async def _process_incoming_message(
        self,
        message: aio_pika.IncomingMessage,
    ):
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

            # Loop over commands. If a command can handle the message, run it.
            # Executes ALL commands able to handle a message, sequentially.
            for command in self.commands:
                if command.can_handle(msg):
                    logger.debug(f"Handling message with {command}")
                    response = command.handle(msg)
                    logger.debug(f"Command produced message: {response}")

                    # Publish the outgoing message to the queue
                    await self.channel.default_exchange.publish(
                        aio_pika.Message(
                            body=response.model_dump_json().encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        ),
                        routing_key="outgoing_messages",
                    )
