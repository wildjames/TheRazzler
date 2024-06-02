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


class SeeQuotedImageCommandHandler(CommandHandler):
    # TODO: This should be a command argument
    reply_filename = "reply.txt"

    def can_handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> bool:
        """Returns True if the message contains a quoted image, False otherwise."""
        if not isinstance(message, IncomingMessage):
            return False

        if not message.envelope.dataMessage:
            return False

        if not message.envelope.dataMessage.quote:
            return False

        for attachment in message.envelope.dataMessage.quote.attachments:
            # We need at least one attachement that is an image
            if attachment.contentType.startswith("image"):
                return True

        return False

    def handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> Iterator[Union[OutgoingReaction, OutgoingMessage, IncomingMessage]]:
        logger.info("Digesting an image message")

        yield self.generate_reaction("🕵️", message)

        gpt = GPTInterface()
        message_text = message.envelope.dataMessage.message

        try:
            images = []
            for attachment in message.envelope.dataMessage.quote.attachments:
                b64_image = self.image_to_base64(attachment.data)
                if attachment.contentType.startswith("image"):
                    images.append(
                        (
                            attachment.contentType,
                            b64_image,
                        )
                    )

            gpt_messages = []
            # TODO: This filename should be a command argument
            describe_image_prompt = load_file("describe_image.txt")
            if describe_image_prompt:
                gpt_messages.append(
                    gpt.create_chat_message(
                        "system",
                        describe_image_prompt.strip(),
                    )
                )

            response = gpt.generate_images_response(
                images, caption=message_text, gpt_messages=gpt_messages
            )
        except Exception as e:
            # give back the failed looking reaction, then terminate the command
            yield self.generate_reaction("❌", message)
            raise e

        yield self.generate_reaction("👁️", message)

        # Replace the message containing the image, with a message containing a
        # description of the image
        parsed_message = message.model_copy()
        if not message_text:
            message_text = ""
        img_description = (
            "The original message contains an image. Image description:"
            f" '{response}'"
        )
        message_text = " | ".join([img_description, message_text])
        parsed_message.envelope.dataMessage.message = message_text
        yield parsed_message

        # Check to see if the Razzler is the only element of the mentions list
        reply = False
        if message.envelope.dataMessage.mentions:
            if len(message.envelope.dataMessage.mentions) == 1:
                mention = message.envelope.dataMessage.mentions[0].number
                logger.info(f"Mentioned: {mention}")
                if mention == config.razzler_phone_number:
                    logger.info(
                        "The razzler was tagged. Posting the message"
                        " description"
                    )
                    reply = True

        if not reply:
            return

        yield self.generate_reaction("🗣️", message)

        try:
            response = self.generate_chat_message(
                config,
                message,
                redis_connection,
                gpt,
                "quality",
            )

            yield OutgoingMessage(
                recipient=self.get_recipient(message), message=response
            )
        except Exception as e:
            yield self.generate_reaction("❌", message)
            raise e
