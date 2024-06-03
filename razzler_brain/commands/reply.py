from logging import getLogger
from typing import Iterator, Optional, Union

import redis

from ai_interface.llm import GPTInterface
from signal_interface.dataclasses import OutgoingReaction

from ..dataclasses import RazzlerBrainConfig
from .base_command import CommandHandler, IncomingMessage, OutgoingMessage

logger = getLogger(__name__)


class ReplyCommandHandler(CommandHandler):
    # TODO: This should be a command argument
    reply_filename = "reply.txt"

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

        # Check if the message has the Razzler as the first mention
        mentions = message.envelope.dataMessage.mentions
        if not mentions:
            return False

        # Check that we have only one mention
        if len(mentions) != 1:
            return False

        # Check that the mention is the Razzler
        return mentions[0].number == config.razzler_phone_number

    def handle(
        self,
        message: IncomingMessage,
        redis_connection: redis.Redis,
        config: RazzlerBrainConfig,
    ) -> Iterator[Union[OutgoingMessage, OutgoingReaction]]:
        logger.info("Handling reply command")

        yield self.generate_reaction("🧠", message)

        # There are three cases.
        # 1. The message contains no images
        # 2. The message contains an image
        # 3. The message contains a quote with an image
        # Note that 2. and 3. are not mutually exclusive - we can have both.

        images = []

        # Handle the case where the message contains an image
        datamessage = message.envelope.dataMessage
        images += self.extract_images(datamessage)

        # Handle the case where the message contains a quote with an image
        quote = message.envelope.dataMessage.quote
        if quote:
            images += self.extract_images(quote)

        logger.info(f"Extracted {len(images)} images from message")

        # Then, get the response.
        try:
            gpt = GPTInterface()
            response = self.generate_chat_message(
                config,
                message,
                redis_connection,
                gpt,
                "quality",
                images,
            )

        except Exception as e:
            logger.error(f"Error creating message: {e}")
            yield self.generate_reaction("❌", message)
            raise e

        response_message = OutgoingMessage(
            recipient=self.get_recipient(message), message=response
        )
        yield response_message

        yield self.generate_reaction("✅", message)
