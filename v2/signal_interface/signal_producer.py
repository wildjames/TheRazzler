import asyncio
import json
from logging import getLogger
from typing import List, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from .signal_api import SignalAPI
from .signal_data_classes import (
    OutgoingMessage,
    OutgoingReaction,
    SignalCredentials,
)

logger = getLogger(__name__)


class SignalProducer:
    """The producer class handles fetching messages from the RabbitMQ queue and
    sending them using the Signal API.
    """

    api_client: SignalAPI
    rabbit_client: pika.BlockingConnection

    def __init__(
        self,
        signal_api_config: SignalCredentials,
        rabbit_config: pika.ConnectionParameters,
    ):
        logger.info("Initializing SignalProducer...")
        self.signal_info = signal_api_config
        self.api_client = SignalAPI(
            signal_api_config.signal_service, signal_api_config.phone_number
        )
        self.rabbit_client = pika.BlockingConnection(rabbit_config)
        self.channel = self.rabbit_client.channel()

    def start(self):
        logger.info("Starting SignalProducer...")

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue="outgoing_messages",
            on_message_callback=self._on_message_callback,
            auto_ack=True,
        )
        logger.info("SignalProducer started. Waiting for messages...")
        self.channel.start_consuming()

    def stop(self):
        logger.info("Stopping SignalProducer...")
        self.channel.stop_consuming()
        self.rabbit_client.close()
        logger.info("SignalProducer stopped.")

    def _on_message_callback(
        self,
        ch: BlockingChannel,
        method: Basic.Deliver,
        properties: pika.BasicProperties,
        body: bytes,
    ):
        logger.info("Received message from RabbitMQ to send.")
        try:
            # Message is a JSON string. It can conform to either
            # OutgoingMessage or OutgoingReaction.

            message_dict = json.loads(body)
            if "reaction" in message_dict:
                outgoing_reaction = OutgoingReaction(**message_dict)
                asyncio.run(self._process_outgoing_reaction(outgoing_reaction))
            else:
                outgoing_message = OutgoingMessage(**message_dict)
                asyncio.run(self._process_outgoing_message(outgoing_message))

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _process_outgoing_message(self, message: OutgoingMessage):
        """Process and send outgoing messages using the Signal API."""
        logger.info(
            f"Sending message to {message.recipient}: {message.message}"
        )
        await self.api_client.send(
            message.recipient, message.message, message.base64_attachments
        )
        logger.info("Message sent successfully.")

    async def _process_outgoing_reaction(self, reaction: OutgoingReaction):
        """Process and send outgoing reactions using the Signal API."""
        logger.info(
            f"Sending reaction to {reaction.recipient}: {reaction.reaction}"
        )
        await self.api_client.react(
            reaction.recipient,
            reaction.reaction,
            reaction.targetAuthor,
            reaction.timestamp,
        )
        logger.info("Reaction sent successfully.")


def admin_message(
    producer: SignalProducer,
    message: str,
    attachments: Optional[List[str]] = None,
):
    """Send a message manually using the producer."""

    msg = OutgoingMessage(
        recipient=producer.signal_info.admin_number,
        message=message,
        base64_attachments=attachments if attachments else [],
    )
    producer.channel.basic_publish(
        exchange="",
        routing_key="outgoing_messages",
        body=msg.model_dump_json(),
    )
    logger.info("Admin message sent.")
