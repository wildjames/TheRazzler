from logging import getLogger
from typing import Iterator, Optional, Union
import uuid

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


class CreateImageCommandHandler(CommandHandler):

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

        return message.envelope.dataMessage.message.lower().startswith("dream")

    def handle(
        self,
        message_id: uuid.UUID,
        message: IncomingMessage,
        redis_connection: redis.Redis,
        config: RazzlerBrainConfig,
    ) -> Iterator[Union[OutgoingMessage, OutgoingReaction]]:
        logger.info(f"[{message_id}] Handling create image command")

        yield self.generate_reaction("🎨", message)

        try:
            gpt = GPTInterface()

            # Trim of the "dream" part of the message to get user-given prompt
            prompt = message.envelope.dataMessage.message[5:]

            # If the user didn't give a prompt, use a default one
            if not prompt:
                user_prefs = self.get_user_prefs(message.get_sender_id())
                prompt = user_prefs.dream_prompt

            prompt = prompt.strip()
            created_images = gpt.generate_image_response(prompt)

            logger.info(
                f"[{message_id}] Creating an image from prompt: {prompt}"
            )

            reply_message = OutgoingMessage(
                recipient=self.get_recipient(message),
                message="Here is your dream.",
                base64_attachments=created_images,
            )

            yield reply_message

        except Exception as e:
            logger.error(f"[{message_id}]Error creating image: {e}")
            self.generate_reaction("❌", message)
            raise e
