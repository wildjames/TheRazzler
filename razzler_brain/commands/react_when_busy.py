import random
from logging import getLogger
from typing import Iterator, Optional
import uuid

import advertools as adv
import redis

from ai_interface.llm import GPTInterface
from razzler_brain.dataclasses import RazzlerBrainConfig
from signal_interface.dataclasses import (
    IncomingMessage,
    OutgoingReaction,
)

from .reply import ReplyCommandHandler

logger = getLogger(__name__)


class ReactToChatCommandHandler(ReplyCommandHandler):
    """Count the number of human messages since the Razzler last spoke: N.
    The razzler generates a number between 0 and 1.
    The threshold to then say something is calculated as:
        (N - minimum_frequency) / (maximum_frequency - minimum_frequency)
    In other words, the razzler starts off unlikely to say something, but
    becomes more likely as the chat becomes more active. Once the maximum
    frequency is reached, the razzler will always say something.
    """

    prompt_key = "react_when_active_chat"

    # TODO: This should be in the user prefs
    frequency = 0.2

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

        if not message.envelope.dataMessage.message:
            return False

        return random.random() < self.frequency

    def extract_first_emoji(self, string: str) -> Optional[str]:
        """Search the string for a valid emoji, left to right. Return the first
        one found, or None if no emoji is found.
        """

    def handle(
        self,
        message_id: uuid.UUID,
        message: IncomingMessage,
        redis_connection: redis.Redis,
        config: RazzlerBrainConfig,
    ) -> Iterator[OutgoingReaction]:
        """Ask the AI to choose a reaction emoji for a message."""

        gpt = GPTInterface()

        response = self.generate_chat_message(
            message_id=message_id,
            config=config,
            message=message,
            prompt_key=self.prompt_key,
            gpt=gpt,
            redis_client=redis_connection,
            model="fast",
        )

        logger.info(
            f"[{message_id}] Asked the Razzler for an emoji. Response:"
            f" '{response}'"
        )
        emoji = adv.extract_emoji([response])
        if not emoji:
            logger.error(f"[{message_id}] No emoji found in response")
            return

        reaction = emoji["emoji_flat"]
        logger.info(f"[{message_id}] Extracted emoji: '{reaction}'")

        reaction = "".join(reaction)
        logger.info(f"[{message_id}] Concatenated emoji: '{reaction}'")

        yield self.generate_reaction(
            emoji=reaction,
            message=message,
        )
