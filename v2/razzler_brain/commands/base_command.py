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
    def publish_message(
        self,
        message: Union[OutgoingMessage, OutgoingReaction],
        channel: BlockingChannel,
    ):
        message_json = message.model_dump_json()
        channel.basic_publish(
            exchange="",
            routing_key="outgoing_messages",
            body=message_json,
            properties=pika.BasicProperties(delivery_mode=2),
        )

    @abstractmethod
    def can_handle(self, message: IncomingMessage) -> bool:
        """Check if the command can handle the given message."""
        pass

    @abstractmethod
    def handle(
        self, message: IncomingMessage, channel: BlockingChannel
    ) -> None:
        """Handle the incoming message and perform actions."""
        pass
