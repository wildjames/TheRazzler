from logging import getLogger
from typing import Iterator, Optional

import redis

from ..dataclasses import RazzlerBrainConfig
from .base_command import CommandHandler, IncomingMessage, OutgoingMessage

logger = getLogger(__name__)


class PingCommandHandler(CommandHandler):

    def can_handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> bool:
        if not isinstance(message, IncomingMessage):
            return False

        if not message.envelope.dataMessage:
            return False

        return message.envelope.dataMessage.message == "ping"

    def handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> Iterator[OutgoingMessage]:
        logger.info("Handling ping command")
        response_message = OutgoingMessage(
            recipient=self.get_recipient(message), message="PONG"
        )
        yield response_message
