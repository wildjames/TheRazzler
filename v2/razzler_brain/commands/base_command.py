from abc import ABC, abstractmethod
from typing import Union

import pika
from pika.adapters.blocking_connection import BlockingChannel
from signal_interface.signal_data_classes import (
    IncomingMessage,
    OutgoingMessage,
    OutgoingReaction,
)


# This needs to be parsable by Pydantic
class CommandHandler(ABC):
    @abstractmethod
    def can_handle(self, message: IncomingMessage) -> bool:
        """Check if the command can handle the given message."""
        pass

    @abstractmethod
    def handle(
        self, message: IncomingMessage, channel: BlockingChannel
    ) -> Union[OutgoingMessage, OutgoingReaction]:
        """Handle the incoming message and perform actions."""
        pass
