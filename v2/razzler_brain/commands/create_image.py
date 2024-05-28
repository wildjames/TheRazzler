from logging import getLogger
from typing import Iterator, Union, Optional

from ai_interface.llm import GPTInterface

from .base_command import (
    CommandHandler,
    IncomingMessage,
    OutgoingMessage,
    OutgoingReaction,
)

logger = getLogger(__name__)


class CreateImageCommandHandler(CommandHandler):
    def can_handle(self, message: IncomingMessage) -> bool:
        if not message.envelope.dataMessage:
            return False

        return message.envelope.dataMessage.message == "dream"

    def handle(
        self, message: IncomingMessage
    ) -> Iterator[Union[OutgoingMessage, OutgoingReaction]]:
        logger.info("Handling create image command")

        reaction_message = OutgoingReaction(
            recipient=self.get_recipient(message),
            reaction="🎨",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )
        yield reaction_message

        gpt = GPTInterface()
        created_images = gpt.create_image_response("Make a dream for me.")

        reply_message = OutgoingMessage(
            recipient=self.get_recipient(message),
            message="Here is your dream.",
            base64_attachments=created_images,
        )

        yield reply_message
