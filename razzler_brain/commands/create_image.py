from logging import getLogger
from typing import Iterator, Optional, Union

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


class CreateImageCommandHandler(CommandHandler):

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

        return message.envelope.dataMessage.message.lower().startswith("dream")

    def handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> Iterator[Union[OutgoingMessage, OutgoingReaction]]:
        logger.info("Handling create image command")

        yield self.generate_reaction("🎨", message)

        try:
            gpt = GPTInterface()

            # Trim of the "dream" part of the message to get user-supplied prompt
            prompt = message.envelope.dataMessage.message[5:]

            # If the user didn't give a prompt, use a default one
            if not prompt:
                # TODO: Make this a command argument
                prompt = load_file("dream_prompt.txt")

            # And if that's not available, use a fallback default one
            if not prompt:
                prompt = (
                    "A dreaming robot screaming into the dark void, as it"
                    " stares back at them."
                )

            prompt = prompt.strip()
            created_images = gpt.generate_image_response(prompt)

            logger.info(f"Creating an image from prompt: {prompt}")

            reply_message = OutgoingMessage(
                recipient=self.get_recipient(message),
                message="Here is your dream.",
                base64_attachments=created_images,
            )

            yield reply_message

        except Exception as e:
            logger.error(f"Error creating image: {e}")
            self.generate_reaction("❌", message)
