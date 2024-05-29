import json
from abc import ABC, abstractmethod
from logging import getLogger
from typing import Iterator, List, Optional, Union

import redis
from ai_interface.llm import GPTInterface
from signal_interface.signal_data_classes import (
    IncomingMessage,
    OutgoingMessage,
    OutgoingReaction,
)
from utils.storage import load_phonebook

from ..dataclasses import RazzlerBrainConfig

logger = getLogger(__name__)


# This needs to be parsable by Pydantic
class CommandHandler(ABC):

    def get_chat_history(
        self, cache_key: str, redis_connection: redis.Redis, gpt: GPTInterface
    ) -> List[str]:
        # Get the message history list from redis
        history = redis_connection.lrange(cache_key, 0, -1)
        # This is in reverse order, so we need to reverse it
        history.reverse()

        messages = []

        # Parse the messages into something the AI can understand
        for msg_str in history:
            msg_dict = json.loads(msg_str)
            # Parse the message into the appropriate type
            models = [IncomingMessage, OutgoingMessage, OutgoingReaction]
            for model in models:
                try:
                    msg = model(**msg_dict)
                    break
                except:
                    pass
            else:
                logger.error(f"Could not parse message: {msg_str}")

            msg_out = ""
            match msg:
                case IncomingMessage():
                    msg_out = (
                        f"{msg.envelope.sourceName}:"
                        f" {msg.envelope.dataMessage.message}"
                    )
                    messages.append(gpt.create_chat_message("user", msg_out))

                case OutgoingMessage():
                    msg_out = f"Razzler: {msg.message}"
                    messages.append(
                        gpt.create_chat_message("assistant", msg_out)
                    )

                case _:
                    continue

        return messages

    @staticmethod
    def get_recipient(message: IncomingMessage) -> str:
        """The sender can be either a single user, or a group."""
        if message.envelope.dataMessage:
            if message.envelope.dataMessage.groupInfo:
                gid = message.envelope.dataMessage.groupInfo.groupId
                phonebook = load_phonebook()
                return phonebook.get_group_internal_id(gid)

        return message.envelope.source

    @abstractmethod
    def can_handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> bool:
        """Check if the command can handle the given message."""
        pass

    @abstractmethod
    def handle(
        self,
        message: IncomingMessage,
        redis_connection: Optional[redis.Redis] = None,
        config: Optional[RazzlerBrainConfig] = None,
    ) -> Iterator[
        Optional[Union[OutgoingMessage, OutgoingReaction, IncomingMessage]]
    ]:
        """Handle the incoming message and perform actions."""
        pass
