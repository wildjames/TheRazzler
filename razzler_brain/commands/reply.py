from datetime import datetime
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

    # We can only reply so many times in a row
    time_window = 60 * 1
    max_replies = 100

    def razzle_history_key(self, recipient: str) -> str:
        return f"razzle_history:{recipient}"

    def count_razzler_messages_in_window(
        self,
        message: IncomingMessage,
        time_window: int,
        redis_connection: redis.Redis,
    ):

        # Get the message history list from redis
        cache_key = self.razzle_history_key(message.get_recipient())
        history = redis_connection.lrange(cache_key, 0, -1)
        # This is a list of datetime strings.
        # Count how many there are in the last time_window seconds
        now = message.envelope.timestamp / 1000
        now = datetime.fromtimestamp(now)

        count = 0
        for timestamp in history:
            timestamp = datetime.fromisoformat(timestamp.decode())
            if (now - timestamp).total_seconds() < time_window:
                count += 1

        logger.info(
            f"Counted {count} messages in the last {time_window} seconds (max"
            f" {self.max_replies})"
        )

        # If we have too many messages in the window, return false
        return count

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

        recent_razzing = self.count_razzler_messages_in_window(
            message, self.time_window, redis_connection
        )
        if recent_razzing >= self.max_replies:
            logger.info(
                f"Too many razzles in the last {self.time_window} seconds."
                f" I've already been summoned {recent_razzing} times."
            )
            yield OutgoingMessage(
                recipient=self.get_recipient(message),
                message=(
                    "I've been summoned"
                    f" {recent_razzing} times in the last"
                    f" {self.time_window/60} minutes, wait a while and"
                    " try again."
                ),
            )
            yield self.generate_reaction("🤫", message)
            return

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

            # The LLM may prefix its messages, so remove them if needed.
            if response.lower().startswith("the razzler"):
                response = response[11:]
            if response.startswith(":"):
                response = response[1:]
            response = response.strip()

        except Exception as e:
            logger.error(f"Error creating message: {e}")
            yield self.generate_reaction("❌", message)
            raise e

        response_message = OutgoingMessage(
            recipient=self.get_recipient(message), message=response
        )
        yield response_message

        # Add the current time to the razzle history list
        cache_key = self.razzle_history_key(message.get_recipient())
        now = datetime.now()
        redis_connection.lpush(cache_key, now.isoformat())

        yield self.generate_reaction("✅", message)
