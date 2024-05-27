"""The Razzler brain listens to the RabbitMQ queue for incoming messages, and
decides how to respond to them. It then sends the responses back to the queue
in the outgoing_messages queue."""

import json
from logging import getLogger
from typing import Union

import pika
import redis
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic
from signal_interface.signal_data_classes import (
    IncomingMessage,
    OutgoingMessage,
    OutgoingReaction,
)
from utils.storage import RedisCredentials

logger = getLogger(__name__)


class RazzlerBrain:
    def __init__(
        self,
        redis_config: RedisCredentials,
        rabbit_config: pika.ConnectionParameters,
    ):
        self.rabbit_client = pika.BlockingConnection(rabbit_config)
        self.channel = self.rabbit_client.channel()
        self.redis_client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
        )

        # Ensure the queue exists
        self.channel.queue_declare(queue="incoming_messages", durable=True)
        self.channel.queue_declare(queue="outgoing_messages", durable=True)

    def start(self):
        """Start consuming messages from RabbitMQ."""
        self.channel.basic_consume(
            queue="incoming_messages",
            on_message_callback=self._process_incoming_message,
            auto_ack=True,
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

        # Prepare response message
        if msg.envelope.dataMessage.message:
            if msg.envelope.dataMessage.message == "ping":
                logger.info(f"Preparing response to {msg.envelope.sourceName}")
                response_message = OutgoingMessage(
                    recipient=msg.envelope.source, message="PONG"
                )
            else:
                response_message = OutgoingReaction(
                    recipient=msg.envelope.source,
                    # React with the horny emoji
                    reaction="🍆",
                    targetAuthor=msg.envelope.sourceUuid,
                    timestamp=msg.envelope.timestamp,
                )

            self.send_response(response_message)

    def send_response(self, message: Union[OutgoingMessage, OutgoingReaction]):
        """Publish a response message to the outgoing_messages queue."""
        logger.debug(f"Publishing text response: {message}")
        self.channel.basic_publish(
            exchange="",
            routing_key="outgoing_messages",
            body=message.model_dump_json(),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.info("Sent response to outgoing_messages queue.")
