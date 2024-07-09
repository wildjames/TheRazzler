from logging import getLogger
from typing import Iterator, Optional
import uuid

import redis

from ai_interface.llm import GPTInterface

from ..dataclasses import RazzlerBrainConfig
from .base_command import (
    CommandHandler,
    IncomingMessage,
    OutgoingMessage,
)

logger = getLogger(__name__)


class SummonCommandHandler(CommandHandler):
    def can_handle(
        self,
        message_id: uuid.UUID,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> bool:
        if not message.envelope.dataMessage:
            return False

        if not isinstance(message.envelope.dataMessage.message, str):
            return False

        return message.envelope.dataMessage.message.lower() == "summon"

    def handle(
        self,
        message_id: uuid.UUID,
        message: IncomingMessage,
        redis_connection: redis.Redis,
        config: RazzlerBrainConfig,
    ) -> Iterator[OutgoingMessage]:
        logger.info(f"[{message_id}] Handling summon command")

        try:
            gpt = GPTInterface()
            response = gpt.generate_chat_completion(
                model="fast",
                messages=[
                    gpt.create_chat_message(
                        "system",
                        "Reply to your summons. You have just been summoned.",
                    ),
                ],
            )

            response_message = OutgoingMessage(
                recipient=self.get_recipient(message), message=response
            )

            yield response_message

        except Exception as e:
            logger.error(f"[{message_id}] Error creating image: {e}")
            yield self.generate_reaction("❌", message)
            raise e
