import base64
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


def image_to_base64(file_path):
    # Read the image file in binary mode
    image_data = load_file(file_path, "rb")

    # Encode the bytes to base64
    encoded_data = base64.b64encode(image_data)

    # Decode bytes to a string (optional, if you need the result as a string)
    encoded_string = encoded_data.decode("utf-8")

    return encoded_string


class SeeImageCommandHandler(CommandHandler):

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

        if not message.envelope.dataMessage.attachments:
            return False

        for attachment in message.envelope.dataMessage.attachments:
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

        yield OutgoingReaction(
            recipient=self.get_recipient(message),
            reaction="🕵️",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )

        gpt = GPTInterface()
        message_text = message.envelope.dataMessage.message

        try:
            images = []
            for attachment in message.envelope.dataMessage.attachments:
                b64_image = image_to_base64(attachment.data)
                images.append(
                    (
                        attachment.contentType,
                        b64_image,
                    )
                )
            response = gpt.get_multiple_image_description(
                images, caption=message_text
            )
        except Exception as e:
            # give back the failed looking reaction, then terminate the command
            yield OutgoingReaction(
                recipient=self.get_recipient(message),
                reaction="😢",
                target_uuid=message.envelope.sourceUuid,
                timestamp=message.envelope.timestamp,
            )
            raise e

        yield OutgoingReaction(
            recipient=self.get_recipient(message),
            reaction="👁️",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )

        # Replace the message containing the image, with a message containing a
        # description of the image
        parsed_message = message.model_copy()
        if not message_text:
            message_text = ""
        img_description = (
            f"This message contains an image. Image description: {response}"
        )
        message_text = " | ".join([message_text, img_description])
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

        yield OutgoingReaction(
            recipient=self.get_recipient(message),
            reaction="🗣️",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )

        personality_text = load_file("personality.txt")
        if not personality_text:
            logger.error("Personality prompt not found")
            return
        logger.info("Personality prompt found")

        gpt_messages = self.get_chat_history(
            f"message_history:{message.get_recipient()}",
            redis_connection,
            gpt,
        )
        gpt_messages.append(
            gpt.create_chat_message("system", personality_text.strip())
        )

        try:
            response = gpt.get_multiple_image_description(
                images, caption=message_text, gpt_messages=gpt_messages
            )
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return

        yield OutgoingMessage(
            recipient=self.get_recipient(message), message=response
        )
