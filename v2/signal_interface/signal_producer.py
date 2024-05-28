import asyncio
import json
from logging import getLogger
from typing import List, Optional

import aio_pika

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

    def __init__(
        self,
        signal_api_config: SignalCredentials,
        rabbit_config: dict,
    ):
        logger.info("Initializing SignalProducer...")
        self.signal_info = signal_api_config
        self.api_client = SignalAPI(
            signal_api_config.signal_service, signal_api_config.phone_number
        )
        self.rabbit_config = rabbit_config
        self.connection = None

    def get_rabbitmq_connection(self):
        return aio_pika.connect_robust(**self.rabbit_config)

    async def _init_mq(self):
        """Asynchronously initialize RabbitMQ connection and channel."""
        self.connection = await self.get_rabbitmq_connection()

        async with self.connection:
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=1)
            # No need to declare exchange if using the default exchange
            await self.channel.declare_queue("outgoing_messages", durable=True)

    async def start(self):
        logger.info("Starting SignalProducer...")
        await self._init_mq()
        await self.consume_messages()

    async def stop(self):
        logger.info("Stopping SignalProducer...")
        await self.connection.close()
        logger.info("SignalProducer stopped.")

    async def consume_messages(self):
        """Consume messages from RabbitMQ and process them."""
        logger.info("Consuming messages from RabbitMQ...")

        if not self.connection or self.connection.is_closed:
            self.connection = await self.get_rabbitmq_connection()

        async with self.connection:
            channel = await self.connection.channel()
            queue = await channel.declare_queue(
                "outgoing_messages", durable=True
            )
            await queue.consume(self._process_message)
            logger.info("Consuming messages...")
            await asyncio.Future()

    async def _process_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                message_dict = json.loads(message.body)
                if "reaction" in message_dict:
                    outgoing_reaction = OutgoingReaction(**message_dict)
                    await self._process_outgoing_reaction(outgoing_reaction)
                else:
                    outgoing_message = OutgoingMessage(**message_dict)
                    await self._process_outgoing_message(outgoing_message)
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
            reaction.target_uuid,
            reaction.timestamp,
        )
        logger.info("Reaction sent successfully.")


async def admin_message(
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
    connection = await aio_pika.connect_robust(**producer.rabbit_config)
    async with connection:
        channel = await connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(msg.__dict__).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="outgoing_messages",
        )
    logger.info("Admin message sent.")
