"""The Razzler brain listens to the RabbitMQ queue for incoming messages, and
decides how to respond to them. It then sends the responses back to the queue
in the outgoing_messages queue."""

import json
from logging import getLogger
from typing import List, Union

import pika
import redis
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic
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
        rabbit_config: pika.ConnectionParameters,
        brain_config: RazzlerBrainConfig,
    ):
        self.rabbit_client = pika.BlockingConnection(rabbit_config)
        self.channel = self.rabbit_client.channel()
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

        # Ensure the queue exists
        self.channel.queue_declare(queue="incoming_messages", durable=True)
        self.channel.queue_declare(queue="outgoing_messages", durable=True)

    def start(self):
        """Start consuming messages from RabbitMQ."""
        self.channel.basic_consume(
            queue="incoming_messages",
            on_message_callback=self._process_incoming_message,
            auto_ack=False,
        )
        logger.info(
            "RazzlerBrain started consuming on incoming_messages queue."
        )
        self.channel.start_consuming()

    def stop(self):
        """Stop the RabbitMQ consumer."""
        self.rabbit_client.close()
        logger.info("RabbitMQ connection closed.")

    def _process_incoming_message(
        self,
        ch: BlockingChannel,
        method: Basic.Deliver,
        properties: pika.BasicProperties,
        body: bytes,
    ):
        logger.info("Processing incoming message...")

        message_data = json.loads(body.decode())
        msg = IncomingMessage(**message_data)
        logger.info(f"Received message: {msg}")

        # Loop over commands. If a command can handle the message, run it.
        # Executes ALL commands able to handle a message, sequentially.
        for command in self.commands:
            if command.can_handle(msg):
                command.handle(msg, self.channel)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def send_response(self, message: Union[OutgoingMessage, OutgoingReaction]):
        """Publish a response message to the outgoing_messages queue."""
        logger.debug(f"Publishing text response: {message}")
        self.channel.basic_publish(
            exchange="",
            routing_key="outgoing_messages",
            body=message.model_dump_json(),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.debug("Sent response to outgoing_messages queue.")
