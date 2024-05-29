from logging import getLogger
from typing import Iterator, Union

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

        if not isinstance(message.envelope.dataMessage.message, str):
            return False

        return message.envelope.dataMessage.message.startswith("dream")

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
        # Trim of the "dream" part of the message
        prompt = message.envelope.dataMessage.message[5:]
        if not prompt:
            prompt = "hyper-real picture of a robot screaming into the void"
        created_images = gpt.create_image_response(prompt)

        reply_message = OutgoingMessage(
            recipient=self.get_recipient(message),
            message="Here is your dream.",
            base64_attachments=created_images,
        )

        yield reply_message
