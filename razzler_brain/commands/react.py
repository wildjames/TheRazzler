from logging import getLogger
from typing import Iterator, Optional

import redis

from ..dataclasses import RazzlerBrainConfig
from .base_command import CommandHandler, IncomingMessage, OutgoingReaction

logger = getLogger(__name__)


class ReactCommandHandler(CommandHandler):
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

        if not message.envelope.dataMessage.message:
            return False

        return message.envelope.dataMessage.message.lower() == "react"

    def handle(
        self,
        message: IncomingMessage,
        redis_connection: redis.Redis,
        config: RazzlerBrainConfig,
    ) -> Iterator[OutgoingReaction]:
        logger.info("Handling react command")
        yield self.generate_reaction(
            message=message,
            emoji="👍",
        )
