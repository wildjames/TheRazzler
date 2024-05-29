import json
from logging import getLogger
from typing import Iterator, List, Optional

import redis
from ai_interface.llm import GPTInterface
from utils.storage import load_file

from ..dataclasses import RazzlerBrainConfig
from .base_command import (
    CommandHandler,
    IncomingMessage,
    OutgoingMessage,
    OutgoingReaction,
)

logger = getLogger(__name__)


class ReplyCommandHandler(CommandHandler):
    insult_filename = "insult.txt"

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
        # If there are, we don't want to handle this message
        if message.envelope.dataMessage.attachments:
            return False

        return mentions[0].number == config.razzler_phone_number

    def handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> Iterator[OutgoingMessage]:
        logger.info("Handling insult command")

        reaction_message = OutgoingReaction(
            recipient=self.get_recipient(message),
            reaction="🧠",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )
        yield reaction_message

        try:
            gpt = GPTInterface()

            personality_prompt = load_file("personality.txt")
            if not personality_prompt:
                raise ValueError("Personality prompt not found")

            # Fetch the insult prompt
            insult_prompt = load_file(self.insult_filename)
            if not insult_prompt:
                raise ValueError("Insult prompt not found")

            messages = []

            cache_key = f"message_history:{message.get_recipient()}"
            history = self.get_chat_history(cache_key, redis_connection, gpt)

            messages.extend(history)
            messages.append(
                gpt.create_chat_message("system", personality_prompt)
            )
            messages.append(gpt.create_chat_message("system", insult_prompt))

            logger.info(
                f"Creating chat completion with {len(messages)} messages"
            )

            response = gpt.generate_chat_completion("quality", messages)

        except Exception as e:
            logger.error(f"Error creating message: {e}")
            yield OutgoingReaction(
                recipient=self.get_recipient(message),
                reaction="❌",
                target_uuid=message.envelope.sourceUuid,
                timestamp=message.envelope.timestamp,
            )
            raise e

        response_message = OutgoingMessage(
            recipient=self.get_recipient(message), message=response
        )
        yield response_message

        done_reaction_message = OutgoingReaction(
            recipient=self.get_recipient(message),
            # success emoji
            reaction="✅",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )
        yield done_reaction_message
