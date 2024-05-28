from logging import getLogger
from typing import Iterator

from .base_command import CommandHandler, IncomingMessage, OutgoingReaction

logger = getLogger(__name__)


class ReactCommandHandler(CommandHandler):
    def can_handle(self, message: IncomingMessage) -> bool:
        if not message.envelope.dataMessage:
            return False

        return message.envelope.dataMessage.message == "react"

    def handle(self, message: IncomingMessage) -> Iterator[OutgoingReaction]:
        logger.info("Handling react command")
        response_message = OutgoingReaction(
            recipient=message.envelope.source,
            reaction="👍",
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )
        yield response_message
