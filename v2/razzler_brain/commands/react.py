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

        return message.envelope.dataMessage.message == "react"

    def handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> Iterator[OutgoingReaction]:
        logger.info("Handling react command")
        response_message = OutgoingReaction(
            recipient=message.envelope.source,
            reaction="👍",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )
        yield response_message
