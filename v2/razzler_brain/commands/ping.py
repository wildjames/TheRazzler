from logging import getLogger

from pika.adapters.blocking_connection import BlockingChannel

from .base_command import CommandHandler, IncomingMessage, OutgoingMessage

logger = getLogger(__name__)


class PingCommandHandler(CommandHandler):
    def can_handle(self, message: IncomingMessage) -> bool:
        return message.envelope.dataMessage.message == "ping"

    def handle(self, message: IncomingMessage) -> OutgoingMessage:
        logger.info("Handling ping command")
        response_message = OutgoingMessage(
            recipient=message.envelope.source, message="PONG"
        )
        return response_message
