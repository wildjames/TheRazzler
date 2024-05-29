from abc import ABC, abstractmethod
from typing import Iterator, Optional, Union

from signal_interface.signal_data_classes import (
    IncomingMessage,
    OutgoingMessage,
    OutgoingReaction,
)
from utils.storage import load_phonebook


# This needs to be parsable by Pydantic
class CommandHandler(ABC):

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
    def can_handle(self, message: IncomingMessage) -> bool:
        """Check if the command can handle the given message."""
        pass

    @abstractmethod
    def handle(
        self, message: IncomingMessage
    ) -> Iterator[
        Optional[Union[OutgoingMessage, OutgoingReaction, IncomingMessage]]
    ]:
        """Handle the incoming message and perform actions."""
        pass
