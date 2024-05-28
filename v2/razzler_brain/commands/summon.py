from logging import getLogger
from typing import Iterator

from ai_interface.llm import GPTInterface

from .base_command import CommandHandler, IncomingMessage, OutgoingMessage

logger = getLogger(__name__)


class SummonCommandHandler(CommandHandler):
    def can_handle(self, message: IncomingMessage) -> bool:
        if not message.envelope.dataMessage:
            return False

        return message.envelope.dataMessage.message == "summon"

    def handle(self, message: IncomingMessage) -> Iterator[OutgoingMessage]:
        logger.info("Handling summon command")

        gpt = GPTInterface()
        response = gpt.create_chat_completion(
            model="fast",
            messages=[
                gpt.create_chat_message(
                    "system",
                    "Reply to your summons. You have just been summoned.",
                ),
            ],
        )

        response_message = OutgoingMessage(
            recipient=self.get_recipient(message), message=response
        )

        yield response_message
