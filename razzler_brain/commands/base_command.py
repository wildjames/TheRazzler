import base64
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from logging import getLogger
from typing import Dict, Iterator, List, Literal, Optional, Tuple, Union

import pydantic
import redis
import tiktoken

from ai_interface.llm import GPTInterface
from signal_interface.dataclasses import (
    DataMessage,
    IncomingMessage,
    OutgoingMessage,
    OutgoingReaction,
    QuoteMessage,
)
from utils.storage import load_file, load_phonebook

from ..dataclasses import RazzlerBrainConfig

logger = getLogger(__name__)


class CommandHandler(ABC):
    # TODO: This is currently quite specialised to work specifically with
    # signal messages. It would be nice to make this more generic, so that it
    # can be used with other messaging services.

    @staticmethod
    def image_to_base64(file_path):
        # Read the image file in binary mode
        image_data = load_file(file_path, "rb")

        # Encode the bytes to base64
        encoded_data = base64.b64encode(image_data)

        # Decode bytes to a string
        # (optional, if you need the result as a string)
        encoded_string = encoded_data.decode("utf-8")

        return encoded_string

    def get_chat_history_for_llm(
        self,
        config: RazzlerBrainConfig,
        cache_key: str,
        redis_connection: redis.Redis,
        gpt: GPTInterface,
        ai_model: Literal["fast", "quality"],
    ) -> List[Dict]:
        """Get the chat history from the cache, and parse it into a format
        that the AI can understand.

        The chat history is returned as a list of dictionaries, where each
        dictionary contains the following keys:
        - sender: The name of the sender
        - content: The content of the message

        Gathers the chat history until the token limit is reached.
        """

        # Get the message history list from redis
        history = redis_connection.lrange(cache_key, 0, -1)

        logger.info(f"Fetched {len(history)} messages from cache")

        messages = []
        num_tokens = 0

        if ai_model == "fast":
            ai_model = gpt.openai_config.fast_model
        elif ai_model == "quality":
            ai_model = gpt.openai_config.quality_model
        else:
            raise ValueError(f"Invalid model: {ai_model}")
        logger.info(f"Using model: {ai_model}")

        enc = tiktoken.encoding_for_model(ai_model)
        logger.info(f"Encoding for model: {enc}")

        # Parse the messages into something the AI can understand
        for msg_str in history:
            msg_dict = json.loads(msg_str)
            # Parse the message into the appropriate type
            msg_models = [IncomingMessage, OutgoingMessage, OutgoingReaction]
            for msg_model in msg_models:
                try:
                    msg = msg_model(**msg_dict)
                    break
                except pydantic.ValidationError:
                    pass
            else:
                logger.error(f"Could not parse message: {msg_str}")

            msg_out = ""
            match msg:
                case IncomingMessage():
                    # Parse the UNIX timestamp (e.g. 1717075009) to a
                    # human-readable format
                    # Irritatingly, the timestamp is in milliseconds
                    ts = msg.envelope.timestamp / 1000
                    time_str = datetime.fromtimestamp(ts).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    # Skips over things like reacts and other non-message
                    # events
                    message_content = msg.envelope.dataMessage.message
                    if message_content:
                        msg_out = (
                            f"{msg.envelope.sourceName} [{time_str}]:"
                            f" {message_content}"
                        )

                        # How many tokens is this message?
                        num_tokens += len(enc.encode(msg_out))

                        # If we've reached the token limit, stop adding
                        # messages and return
                        if num_tokens < config.max_chat_history_tokens:
                            messages.append(
                                gpt.create_chat_message("user", msg_out)
                            )
                        else:
                            logger.info(
                                f"Reached token limit at: {num_tokens} tokens"
                                f" over {len(messages)} messages"
                            )
                            # We built the messages history in reverse order,
                            # starting with the most recent, so we need to
                            # reverse it
                            messages.reverse()

                            if len(messages):
                                logger.info(f"Oldest message: {messages[0]}")
                                logger.info(
                                    f"Most recent message: {messages[-1]}"
                                )
                            else:
                                logger.info("No messages in history")

                            return messages

                case OutgoingMessage():
                    msg_out = f"Razzler: {msg.message}"
                    messages.append(
                        gpt.create_chat_message("assistant", msg_out)
                    )

                case _:
                    continue

        messages.reverse()

        if len(messages):
            logger.info(f"Oldest message: {messages[0]}")
            logger.info(f"Most recent message: {messages[-1]}")
        else:
            logger.info("No messages in history")
        return messages

    def generate_chat_message(
        self,
        config: RazzlerBrainConfig,
        message: IncomingMessage,
        redis_client: redis.Redis,
        gpt: GPTInterface,
        model: Literal["fast", "quality"],
        images: Optional[List[Tuple[str, str]]] = None,
    ) -> str:
        """Generate a chat message in response to the given message.
        Note that images can be attached, but they're assumed to be
        associated with the incoming message. Past images are not parsed.

        Model can be either "fast" or "quality"."""

        personality_prompt = load_file("personality.txt")
        if not personality_prompt:
            raise ValueError("Personality prompt not found")

        # Fetch the reply prompt
        reply_prompt = load_file(self.reply_filename)
        if not reply_prompt:
            raise ValueError("reply prompt not found")

        messages = []

        cache_key = f"message_history:{message.get_recipient()}"
        history = self.get_chat_history_for_llm(
            config, cache_key, redis_client, gpt, model
        )

        messages.extend(history)

        # If we have images, add them to the message content
        if images:
            logger.info("Injecting image data into the chat history")
            # Loop backwards, since we want to inject the data into a recent
            # message
            for m in messages[::-1]:
                if message.envelope.dataMessage.message in m["content"]:
                    logger.info(f"Found the corresponding message: {m}")
                    # update the content of the message with the image(s)
                    image_message = gpt.create_image_message(
                        images, m["content"]
                    )

                    # Process the old message content
                    message_body = m["content"]

                    # And update the content with its new data
                    m["content"] = image_message["content"]

                    # Remove previous image descriptions, which are enclosed by
                    # [[[ and ]]]
                    message_body = re.sub(r"\[\[\[.*?\]\]\]", "", message_body)

                    # Push the old message content back into the caption
                    logger.info(f"Old message content: {message_body}")
                    m["content"][0]["text"] = message_body

                    break

        messages.append(gpt.create_chat_message("system", personality_prompt))
        messages.append(gpt.create_chat_message("system", reply_prompt))

        logger.info(f"Creating chat completion with {len(messages)} messages")

        response = gpt.generate_chat_completion(model, messages)
        if response.lower().startswith("razzler:"):
            response = response[8:]
        response = response.strip()

        return response

    def generate_reaction(
        self,
        emoji: str,
        message: IncomingMessage,
    ) -> OutgoingReaction:
        return OutgoingReaction(
            recipient=message.get_recipient(),
            reaction=emoji,
            target_uuid=message.envelope.sourceUuid,
            timestamp=message.envelope.timestamp,
        )

    def extract_images(
        self, message: Union[DataMessage, QuoteMessage]
    ) -> List[Tuple[str, str]]:
        """Get the image data from images contained in the message directly,
        or those contained in the message's quotes.

        Returns a list of tuples, where the first element is the content type
        of the image, and the second element is the base64-encoded image data.
        """

        images = []

        for attachment in message.attachments:
            if attachment.contentType.startswith("image"):
                b64_image = self.image_to_base64(attachment.data)
                images.append(
                    (
                        attachment.contentType,
                        b64_image,
                    )
                )

        return images

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
        redis_connection: redis.Redis,
        config: RazzlerBrainConfig,
    ) -> Iterator[
        Optional[Union[OutgoingMessage, OutgoingReaction, IncomingMessage]]
    ]:
        """Handle the incoming message and perform actions."""
        pass
