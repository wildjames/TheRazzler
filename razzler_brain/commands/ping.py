from logging import getLogger
from typing import Iterator, Optional
import uuid

import redis

from ..dataclasses import RazzlerBrainConfig
from .base_command import CommandHandler, IncomingMessage, OutgoingMessage

logger = getLogger(__name__)


class PingCommandHandler(CommandHandler):

    def can_handle(
        self,
        message_id: uuid.UUID,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> bool:
        if not isinstance(message, IncomingMessage):
            return False

        if not message.envelope.dataMessage:
            return False

        if not isinstance(message.envelope.dataMessage.message, str):
            return False

        return message.envelope.dataMessage.message.lower() == "ping"

    def handle(
        self,
        message_id: uuid.UUID,
        message: IncomingMessage,
        redis_connection: redis.Redis,
        config: RazzlerBrainConfig,
    ) -> Iterator[OutgoingMessage]:
        logger.info(f"[{message_id}] Handling ping command")
        response_message = OutgoingMessage(
            recipient=self.get_recipient(message), message="PONG"
        )
        yield response_message
