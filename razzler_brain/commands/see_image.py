import re
from logging import getLogger
from typing import Iterator, List, Optional, Tuple, Union
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


class SeeImageCommandHandler(CommandHandler):
    """Replace the IncomingMessage in the message history, such that it
    contains the image description. The image description is generated using
    an openAI model.

    Injected image descriptions are enclosed in [[[ ]]] brackets.
    """

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

        if not message.envelope.dataMessage.attachments:
            return False

        for attachment in message.envelope.dataMessage.attachments:
            if attachment.contentType.startswith("image"):
                return True

        return False

    def handle(
        self,
        message_id: uuid.UUID,
        message: IncomingMessage,
        redis_connection: redis.Redis,
        config: RazzlerBrainConfig,
    ) -> Iterator[Union[OutgoingReaction, OutgoingMessage, IncomingMessage]]:
        logger.info(f"[{message_id}] Digesting an image message")
        yield self.generate_reaction("🕵️", message)

        # There are two cases, one where the image is attached to the message
        # and the other where the image is quoted in the message.

        try:
            # Handle the case where the image is attached to the message
            images = self.extract_images(message.envelope.dataMessage)

            if images:
                logger.info(
                    f"[{message_id}] Extracted {len(images)} images from"
                    " message"
                )
                response = self.generate_images_description(
                    message_id, images, message
                )
                yield self.update_message_with_description(message, response)

            # Handle the case where the image is quoted in the message
            if message.envelope.dataMessage.quote:
                logger.info(f"[{message_id}] This message contains a quote")
                images = self.extract_images(
                    message.envelope.dataMessage.quote
                )

                if images:
                    logger.info(
                        f"[{message_id}] Extracted {len(images)} images from"
                        " quote"
                    )
                    response = self.generate_images_description(
                        message_id, images, message
                    )
                    yield self.update_quote_with_description(message, response)

        except Exception as e:
            yield self.generate_reaction("❌", message)
            raise e

        yield self.generate_reaction("👁️", message)

    def generate_images_description(
        self,
        message_id: uuid.UUID,
        images: List[Tuple[str, str]],
        message: IncomingMessage,
    ):
        gpt = GPTInterface()

        # Get the user preference for image descriptions
        user_prefs = self.get_user_prefs(message.get_sender_id())
        describe_image_prompt = user_prefs.describe_image
        logger.info(
            f"[{message_id}] Describing image using prompt:"
            f" {describe_image_prompt}"
        )

        gpt_messages = [
            gpt.create_chat_message("system", describe_image_prompt.strip())
        ]
        return gpt.generate_images_response(
            images,
            caption=message.envelope.dataMessage.message,
            gpt_messages=gpt_messages,
        )

    def update_message_with_description(
        self, message: IncomingMessage, description: str
    ) -> IncomingMessage:
        """Given an incoming message and an image description, update the
        message with the image description."""

        parsed_message = message.model_copy()
        img_description = (
            "[[[This message contains an image. Image description:"
            f" '{description}']]]"
        )

        # Concatenate the image description with the original message
        # (At least one exists, possibly both)
        message_text = " ".join(
            filter(
                None, [message.envelope.dataMessage.message, img_description]
            )
        )

        # Return the updated message
        parsed_message.envelope.dataMessage.message = message_text
        return parsed_message

    def update_quote_with_description(
        self, message: IncomingMessage, description: str
    ) -> IncomingMessage:
        """Given an incoming message and an image description, update the
        quoted message with the image description."""

        parsed_message = message.model_copy()
        img_description = (
            "[[[This message contains an image. Image description:"
            f" '{description}']]]"
        )

        # Build a new message with the image description and the quoted message
        # Remove the quote from the original message
        scrubbed_msg = re.sub(
            r"\[Quote\].*\[End quote\]",
            "",
            message.envelope.dataMessage.message,
        )

        quote = message.envelope.dataMessage.quote
        message_text = (
            "[Quote]\n"
            "In reply to"
            f' {quote.author}:\n"{quote.text}"\n{img_description}\n[End'
            f" quote]\n\n{scrubbed_msg}"
        )

        # Return the updated message
        parsed_message.envelope.dataMessage.message = message_text
        return parsed_message
