from .base_command import CommandHandler, IncomingMessage, OutgoingReaction

from logging import getLogger

logger = getLogger(__name__)


class ReactCommandHandler(CommandHandler):
    def can_handle(self, message: IncomingMessage) -> bool:
        return message.envelope.dataMessage.message == "react"

    def handle(self, message: IncomingMessage, channel):
        logger.info("Handling react command")
        response_message = OutgoingReaction(
            recipient=message.envelope.source,
            reaction="👍",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )
        self.publish_message(response_message, channel)
