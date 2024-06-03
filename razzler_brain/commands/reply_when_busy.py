import json
from logging import getLogger
from typing import Optional

import pydantic
import redis

from razzler_brain.dataclasses import RazzlerBrainConfig
from signal_interface.dataclasses import IncomingMessage, OutgoingMessage

from .reply import ReplyCommandHandler

logger = getLogger(__name__)


class ReplyWhenActiveChatCommandHandler(ReplyCommandHandler):
    def can_handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> bool:
        """This command triggers if 10 messages are sent within 60 second of each
        other, but only if no messages have a mention of the razzler and
        no messages originate from the razzler.
        """

        if not isinstance(message, IncomingMessage):
            return False

        cache_key = f"message_history:{message.get_recipient()}"
        history = redis_connection.lrange(cache_key, 0, -1)

        if len(history) < 2:
            return False

        # Each incoming message has a timestamp. Count how many messages were
        # sent within some number of seconds of the current message.
        time_window = 60000  # ms
        required_msgs = 10

        count = 0
        last_msg_time = message.envelope.timestamp
        for record in history:
            try:
                msg = IncomingMessage(**json.loads(record))

                this_timestamp = msg.envelope.timestamp
                if abs(this_timestamp - last_msg_time) < time_window:
                    count += 1
            except pydantic.ValidationError:
                # If the window contains a razzler message, then don't trigger
                # We don't want to dominate the conversation
                try:
                    OutgoingMessage(**json.loads(record))

                    this_timestamp = msg.envelope.timestamp
                    if abs(this_timestamp - last_msg_time) < time_window:
                        logger.info(
                            "The chat is active, but I already replied at"
                            f" {this_timestamp}"
                        )
                        return False

                except pydantic.ValidationError:
                    continue

                # If the record is not a valid IncomingMessage, skip it.
                continue

        logger.info(
            f"Found {count} messages within {time_window/1000} seconds"
        )

        return count >= required_msgs
