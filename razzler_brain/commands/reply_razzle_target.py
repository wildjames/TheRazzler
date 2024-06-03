from logging import getLogger
from typing import Optional

import redis

from ..dataclasses import RazzlerBrainConfig
from .base_command import IncomingMessage
from .reply import ReplyCommandHandler

logger = getLogger(__name__)


class ReplyRazzleTargetCommandHandler(ReplyCommandHandler):
    # TODO: This should be a command argument
    reply_filename = "reply_razzle_target.txt"

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

        # Check if the message has the Razzler as the first mention
        mentions = message.envelope.dataMessage.mentions
        if not mentions:
            return False

        # Check that we more than one mentioned user
        if len(mentions) < 2:
            return False

        # Check that the mention is the Razzler
        if mentions[0].number != config.razzler_phone_number:
            return False

        return True
