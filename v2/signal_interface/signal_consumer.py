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
import pika
from pika.adapters.blocking_connection import BlockingChannel

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

    api_client: SignalAPI
    signal_info: SignalCredentials
    event_loop: asyncio.AbstractEventLoop
    rabbit_client: pika.BlockingConnection
    redis_client: redis.Redis
    channel: BlockingChannel
    phonebook: PhoneBook

    def __init__(
        self,
        signal_info: SignalCredentials,
        redis_config: RedisCredentials,
        rabbit_config: pika.ConnectionParameters,
    ):
        logger.info("Initializing SignalConsumer...")
        self.api_client = SignalAPI(
            signal_info.signal_service, signal_info.phone_number
        )
        self.signal_info = signal_info
        self.rabbit_client = pika.BlockingConnection(rabbit_config)
        self.redis_client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
        )

        self.phonebook = load_phonebook()

        self._init_queue()
        self._init_mq()

    def _init_queue(self):
        logger.info("Initializing scheduler...")
        self.event_loop = asyncio.get_event_loop()
        self._asyncio_queue = asyncio.Queue()
        logger.info("Scheduler initialized.")

    def _init_mq(self):
        """Initialize RabbitMQ connection and declare the queue."""
        self.channel = self.rabbit_client.channel()
        self.channel.queue_declare(queue="incoming_messages", durable=True)
        self.channel.queue_declare(queue="outgoing_messages", durable=True)
        logger.info("Connected to RabbitMQ and declared the queues.")

    def start(self):
        logger.info(
            f"Starting SignalConsumer for {self.signal_info.phone_number}..."
        )
        # Create a task to listen for incoming messages
        self.event_loop.create_task(self.listen())

        logger.info("Scheduler started. Running event loop...")
        self.event_loop.run_forever()
        logger.info("Event loop stopped.")

    def stop(self):
        self.event_loop.stop()
        logger.info("Stopped scheduler and event loop. Stopped SignalConsumer")

    async def listen(self):
        """Check for new messages to add to the message queue."""
        async for raw_message in self.api_client.receive():
            message = json.loads(raw_message)

            logger.debug(f"Signal API yielded the message: {message}")
            # Add a queue item to process the incoming message
            self.event_loop.create_task(self._process_incoming(message))

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
            serialized_message = msg.model_dump_json()
            self.channel.basic_publish(
                exchange="",
                routing_key="incoming_messages",
                body=serialized_message,
                # make message persistent
                properties=pika.BasicProperties(delivery_mode=2),
            )
            logger.info(
                "Added message to the processing queue: Timestamp"
                f" {msg.envelope.timestamp} from {msg.envelope.sourceNumber}"
            )
            return
