import asyncio
import json
from logging import getLogger
from typing import List, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from .signal_api import SignalAPI
from .signal_data_classes import OutgoingMessage, SignalCredentials

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
            outgoing_message = OutgoingMessage(**json.loads(body))
            asyncio.run(self._process_outgoing_message(outgoing_message))
            logger.info("Processed and acknowledged message.")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            ch.basic_ack(delivery_tag=method.delivery_tag, requeue=True)

    async def _process_outgoing_message(self, message: OutgoingMessage):
        """Process and send outgoing messages using the Signal API."""
        logger.info(
            f"Sending message to {message.recipient}: {message.message}"
        )
        await self.api_client.send(
            message.recipient, message.message, message.base64_attachments
        )
        logger.info("Message sent successfully.")


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
