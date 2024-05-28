from logging import getLogger
from typing import Iterator

from .base_command import CommandHandler, IncomingMessage, OutgoingMessage

logger = getLogger(__name__)


class PingCommandHandler(CommandHandler):
    def can_handle(self, message: IncomingMessage) -> bool:
        if not message.envelope.dataMessage:
            return False

        return message.envelope.dataMessage.message == "ping"

    def handle(self, message: IncomingMessage) -> Iterator[OutgoingMessage]:
        logger.info("Handling ping command")
        response_message = OutgoingMessage(
            recipient=self.get_recipient(message), message="PONG"
        )
        yield response_message
