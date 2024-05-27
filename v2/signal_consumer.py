"""This scripts should create a bot that gets and stores incoming messages from
the signal server (use the signal API class provided).

Incoming messages are checked periodically, and stored in a redis queue.
"""

import asyncio
import json
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any, Dict, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redis import Redis

from signal_api import SignalAPI
from signal_message_classes import IncomingMessage, OutgoingMessage

logger = getLogger(__name__)


@dataclass
class Contact:
    name: str
    number: str


@dataclass
class SignalInformation:
    # URL of the signal API server
    signal_service: str
    # My phone number
    phone_number: str
    # This is the administrator's phone number. They have special privileges,
    # and receive status updates when appropriate.
    admin_number: str
    # A list of contacts known to the bot.
    contacts: List[Contact] = field(default_factory=list)
    # A list of groups that the bot is a member of. Will be auto-populated
    # from the signal server.
    groups: List[str] = field(default_factory=list)


class SignalConsumer:
    """The consumer class handles checking for new messages, and placing them
    on the queue.
    """

    api_client: SignalAPI
    signal_info: SignalInformation
    event_loop: asyncio.AbstractEventLoop

    def __init__(self, signal_info: SignalInformation, redis_client: Redis):
        logger.info("Initializing SignalConsumer...")
        self.api_client = SignalAPI(
            signal_info.signal_service, signal_info.phone_number
        )
        self.signal_info = signal_info
        self.redis_client = redis_client

        # Handle the contacts list (get contacts, add contacts
        self._init_contacts()

        # Handle group chat setups (listen and whitelist my groups)
        self._init_groups()

        self._init_queue()

    def _init_contacts(self):
        """This method should initialize the contacts list."""
        # TODO
        pass

    def _init_groups(self):
        """This method handles group chat setups."""
        # TODO
        pass

    def _init_queue(self):
        logger.info("Initializing scheduler...")
        self.event_loop = asyncio.get_event_loop()
        self._asyncio_queue = asyncio.Queue()
        logger.info("Scheduler initialized.")

    def start(self):
        logger.info(
            f"Starting SignalConsumer for {self.signal_info.phone_number}..."
        )
        # Create a task to listen for incoming messages
        self.event_loop.create_task(self.listen())

        started_message = OutgoingMessage(
            recipient=self.signal_info.admin_number,
            message="SignalConsumer started.",
        )
        self.event_loop.create_task(self._process_outgoing(started_message))

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
        logger.debug(f"Processing incoming message")

        # Parse the json payload to an IncomingMessage object
        msg = IncomingMessage(**message)
        logger.info(f"Converted message: {msg}")

        if msg.envelope.typingMessage:
            logger.info(
                f"Typing message received: {msg.envelope.typingMessage.action}"
            )
            return

        if msg.envelope.receiptMessage:
            logger.info(
                "Receipt message received. Has the message been read?"
                f" {msg.envelope.receiptMessage.isRead}"
            )
            return

        if msg.envelope.dataMessage:
            logger.debug(f"Data message received")
            data = msg.envelope.dataMessage

            # Do we have a reaction?
            if data.reaction:
                logger.info(
                    f"Reaction received: {data.reaction} @ {data.message}"
                )
                return

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

            # Do we have a message?
            if data.message:
                logger.info(f"Text message received: {data.message}")

                resp = await self.api_client.react(
                    recipient=msg.envelope.sourceUuid,
                    reaction="👍",
                    target_author=msg.envelope.sourceUuid,
                    timestamp=msg.envelope.timestamp,
                )
                logger.debug(f"Reaction response: {resp}")

            # Add the message to the processing queue
            logger.warn("📩 I need to add this message to the queue")
            return

    async def _process_outgoing(self, message: OutgoingMessage):
        """Process outgoing messages."""
        logger.info(f"Processing outgoing message: {message}")
        await self.api_client.send(
            message.recipient,
            message.message,
            message.base64_attachments,
        )
        logger.info(f"Sent message: {message.message}")
