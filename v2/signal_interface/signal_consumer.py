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

import redis
import aio_pika

from .signal_api import SignalAPI
from .signal_data_classes import (
    IncomingMessage,
    SignalCredentials,
)
from utils.phonebook import PhoneBook
from utils.storage import load_phonebook, RedisCredentials

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
        self.redis_client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
        )

        self.phonebook = load_phonebook()

        # RabbitMQ connection
        self.connection = None

        logger.info("SignalConsumer initialized.")

    def get_rabbitmq_connection(self):
        return aio_pika.connect_robust(**self.rabbit_config)

    async def _init_mq(self):
        """Initialize RabbitMQ connection and declare the queue asynchronously."""
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
        msg = IncomingMessage(**message)
        logger.debug("Parsed incoming message payload")

        # These are messages to ignore - read receipts, typing indicators, etc.
        if msg.envelope.typingMessage:
            logger.debug(
                f"Typing message received: {msg.envelope.typingMessage.action}"
            )
            return

        if msg.envelope.receiptMessage:
            logger.debug(
                "Receipt message received. Has the message from timestamp"
                f" {msg.envelope.timestamp} been read?"
                f" {msg.envelope.receiptMessage.isRead}"
            )
            return

        # We only care about publishing data messages
        if msg.envelope.dataMessage:
            logger.debug("Data message received")
            data = msg.envelope.dataMessage

            # If it has an attachement, we need to download it
            if data.attachments:
                logger.info("Message has attachments.")
                for attachment in data.attachments:
                    logger.info(f"Downloading attachment: {attachment.id}")
                    attachment.base64 = (
                        await self.api_client.download_attachment(
                            attachment.id
                        )
                    )
                    logger.debug(f"Downloaded attachment: {attachment.id}")

            # Add the message to the processing queue
            await self._publish_message(msg)
