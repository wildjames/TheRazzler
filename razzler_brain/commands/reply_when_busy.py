import json
import random
from logging import getLogger
from typing import Optional

import pydantic
import redis

from razzler_brain.dataclasses import RazzlerBrainConfig
from signal_interface.dataclasses import IncomingMessage, OutgoingMessage

from .reply import ReplyCommandHandler

logger = getLogger(__name__)


class ReplyWhenActiveChatCommandHandler(ReplyCommandHandler):
    """Count the number of human messages since the Razzler last spoke: N.
    The razzler generates a number between 0 and 1.
    The threshold to then say something is calculated as:
        (N - minimum_frequency) / (maximum_frequency - minimum_frequency)
    In other words, the razzler starts off unlikely to say something, but
    becomes more likely as the chat becomes more active. Once the maximum
    frequency is reached, the razzler will always say something.
    """

    minumum_frequency = 5
    maximum_frequency = 100

    # Maximum time to scan, in seconds.
    time_window = 60 * 60 * 3

    def can_handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> bool:

        if not isinstance(message, IncomingMessage):
            return False

        cache_key = f"message_history:{message.get_recipient()}"
        history = redis_connection.lrange(cache_key, 0, -1)

        if len(history) < 2:
            return False

        # Each incoming message has a timestamp. Count how many messages were
        # sent within some number of seconds of the current message.
        time_window = self.time_window * 1000  # ms

        count = 0
        last_msg_time = message.envelope.timestamp
        for record in history:
            try:
                msg = IncomingMessage(**json.loads(record))

                if not msg.envelope.dataMessage:
                    # Don't count receipt messages
                    continue

                this_timestamp = msg.envelope.timestamp
                if abs(this_timestamp - last_msg_time) > time_window:
                    break

                count += 1
                logger.debug(
                    f"Counting message: {msg.envelope.dataMessage.message}"
                )
            except pydantic.ValidationError:
                # If the window contains a razzler message, stop counting
                try:
                    OutgoingMessage(**json.loads(record))

                    logger.debug(
                        f"Found a razzler reply. Stopping counting messages"
                    )
                    break

                except pydantic.ValidationError:
                    # If we get here, it's an OutgoingReaction
                    continue

        logger.info(
            f"Found {count} messages within {self.time_window} seconds"
        )

        chance = (count - self.minumum_frequency) / (
            self.maximum_frequency - self.minumum_frequency
        )
        # constrain the chance to be between 0 and 1
        chance = max(0, min(1, chance))
        logger.info(f"This gives the razzler a {chance:.3f} chance to reply")

        r = random.random()
        return r < chance
