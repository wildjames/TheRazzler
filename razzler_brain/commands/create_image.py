from logging import getLogger
from typing import Iterator, Optional, Union

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

        reaction_message = OutgoingReaction(
            recipient=self.get_recipient(message),
            reaction="🎨",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )
        yield reaction_message

        try:
            gpt = GPTInterface()
            # Trim of the "dream" part of the message
            prompt = message.envelope.dataMessage.message[5:]
            if not prompt:
                prompt = (
                    "hyper-real picture of a robot screaming into the void"
                )
            prompt = prompt.strip()
            created_images = gpt.create_image_response(prompt)

            reply_message = OutgoingMessage(
                recipient=self.get_recipient(message),
                message="Here is your dream.",
                base64_attachments=created_images,
            )

            yield reply_message

        except Exception as e:
            logger.error(f"Error creating image: {e}")
            yield OutgoingReaction(
                recipient=self.get_recipient(message),
                reaction="😢",
                target_uuid=message.envelope.sourceUuid,
                timestamp=message.envelope.timestamp,
            )
