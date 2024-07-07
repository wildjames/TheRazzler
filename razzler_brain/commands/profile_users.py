from logging import getLogger
from typing import Iterator, Optional

import redis

from ..dataclasses import RazzlerBrainConfig
from .base_command import CommandHandler, IncomingMessage, OutgoingMessage

logger = getLogger(__name__)


class CharacterProfileCommandHandler(CommandHandler):

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

        if not isinstance(message.envelope.dataMessage.message, str):
            return False

        # I need some record of how long it's been since we profiled this group

    def handle(
        self,
        message: IncomingMessage,
        redis_connection: redis.Redis,
        config: RazzlerBrainConfig,
    ) -> Iterator[None]:

        logger.info(
            "Creating character profiles of chat members" f" {message.get_recipient()}"
        )
        response_message = OutgoingMessage(
            recipient=self.get_recipient(message),
            message=("Hold on, I need to take some notes on what you're saying..."),
        )
        yield response_message
