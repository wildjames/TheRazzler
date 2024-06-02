import json
from logging import getLogger
from typing import Iterator, List, Optional

import redis

from ai_interface.llm import GPTInterface

from ..dataclasses import RazzlerBrainConfig
from .base_command import (
    CommandHandler,
    IncomingMessage,
    OutgoingMessage,
    OutgoingReaction,
)

logger = getLogger(__name__)


class ReplyCommandHandler(CommandHandler):
    # TODO: This should be a command argument
    reply_filename = "reply.txt"

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

        # Check if there are any image attachments.
        # If there are, we don't want to handle this message - the image
        # handler should take care of it.
        if message.envelope.dataMessage.attachments:
            return False
        # Or, if there are any quote attachments.
        if message.envelope.dataMessage.quote:
            if message.envelope.dataMessage.quote.attachments:
                return False

        return mentions[0].number == config.razzler_phone_number

    def handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> Iterator[OutgoingMessage]:
        logger.info("Handling reply command")

        yield self.generate_reaction("🧠", message)

        try:
            gpt = GPTInterface()
            response = self.generate_chat_message(
                config,
                message,
                redis_connection,
                gpt,
                "quality",
            )

        except Exception as e:
            logger.error(f"Error creating message: {e}")
            yield self.generate_reaction("❌", message)
            raise e

        response_message = OutgoingMessage(
            recipient=self.get_recipient(message), message=response
        )
        yield response_message

        yield self.generate_reaction("✅", message)
