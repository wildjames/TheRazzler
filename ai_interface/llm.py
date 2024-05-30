import json
import random
import re
from logging import getLogger
from typing import Dict, Iterator, List, Optional, Tuple

import openai
import yaml
from openai.resources.chat.completions import ChatCompletionMessageParam
from openai.types.chat.chat_completion import ChatCompletion, Choice
from utils.storage import load_file, load_file_lock

from .dataclasses import OpenAIConfig

logger = getLogger(__name__)


def clean_filename(filename):
    # Replaces non-alphanumeric characters (except for periods, hyphens and
    # underscores) with an underscore
    filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    # Replaces any remaining forward slashes with an underscore
    filename = filename.replace("/", "_")
    return filename


class GPTInterface:
    """The GPTInterface class is responsible for managing OpenAI models,
    and parsing signal models into a form that can be read by the OpenAI API.

    Redis is used to cache the recent message history.
    """

    openai_config: OpenAIConfig
    llm: openai.OpenAI

    def __init__(self):
        logger.info("Initializing GPTInterface...")

        config = yaml.safe_load(load_file("config.yaml"))

        self.openai_config = OpenAIConfig(**config["openai"])
        logger.info(f"OpenAI config: {self.openai_config}")

        self.llm = openai.OpenAI()

    def reset(self):
        self.total_prompt_tokens = {}
        self.total_completion_tokens = {}

    def generate_chat_completion(
        self,
        model: str,
        messages: List[str],
    ) -> str:
        match model:
            case "fast":
                use_model = self.openai_config.fast_model
            case "quality":
                use_model = self.openai_config.quality_model
            case _:
                raise ValueError(f"Invalid model: {model}")

        logger.info(f"Creating chat completion with {len(messages)} messages")
        for m in messages:
            logger.info(m)

        response: ChatCompletion = self.llm.chat.completions.create(
            messages=messages,
            model=use_model,
            # Pass in the kwargs from the config file
            **self.openai_config.chat_completion_kwargs,
        )

        self.update_costs(response)

        chosen_response: Choice = random.choice(response.choices)

        return chosen_response.message.content

    def create_chat_message(
        self, role: str, content: str
    ) -> ChatCompletionMessageParam:
        """
        Create a chat message with the given role and content.

        Args:
        role (str): The role of the message sender, e.g., "system", "user", or
            "assistant".
        content (str): The content of the message.

        Returns:
        dict: A dictionary containing the role and content of the message.
        """
        return {"role": role, "content": content}

    def generate_images_response(
        self,
        images: List[Tuple[str, str]],
        caption: Optional[str] = None,
        gpt_messages: Optional[List[str]] = None,
    ) -> str:
        """Describe a series of images. The images should be a list of tuples,
        where each tuple contains the image format and base64-encoded image
        in that order.
        """
        if gpt_messages is None:
            gpt_messages = []

        if caption in ["", None]:
            caption = "Describe the images you see."

        gpt_messages.append(self.create_image_message(images, caption))

        response: ChatCompletion = self.llm.chat.completions.create(
            messages=gpt_messages,
            model=self.openai_config.vision_model,
            **self.openai_config.vision_completion_kwargs,
        )

        self.update_costs(response)

        chosen_response: Choice = random.choice(response.choices)

        return chosen_response.message.content

    def create_image_message(
        self, images: Iterator[Tuple[str, str]], image_caption: str = ""
    ) -> ChatCompletionMessageParam:
        """
        Create a chat message with the given image format and base64 image.

        Args:
        image_format (str): The format of the image, e.g., "image/jpeg" or
            "image/png".
        b64_image (str): The base64-encoded image.

        Returns:
        dict: A message for the chat API containing the image.
        """
        message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": image_caption,
                },
            ],
        }

        for image_format, b64_image in images:
            message["content"] += (
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_format};base64,{b64_image}",
                        # "detail": "low",
                    },
                },
            )

        return message

    def generate_image_response(self, prompt: str) -> List[str]:
        """Use the image generation model to create an image"""
        response = self.llm.images.generate(
            model=self.openai_config.image_model,
            prompt=prompt,
            response_format="b64_json",
            **self.openai_config.image_generation_kwargs,
        )

        images = [r.b64_json for r in response.data]
        return images

    def update_costs(self, response: ChatCompletion):
        """Update the costs of the models. Syncs the usage with the file."""
        logger.info(f"Updating costs from message: {response}")

        with load_file_lock("llm_usage.json") as f:
            usage_str = f.read()
            if not usage_str:
                usage_str = "{}"
            usage: Dict = json.loads(usage_str)

            used_model = response.model
            prev_p_tokens = usage.get(used_model, {}).get("prompt_tokens", 0)
            prev_c_tokens = usage.get(used_model, {}).get(
                "completion_tokens", 0
            )

            usage[used_model] = {
                "prompt_tokens": prev_p_tokens + response.usage.prompt_tokens,
                "completion_tokens": prev_c_tokens
                + response.usage.completion_tokens,
            }

            logger.debug(f"Usage updated: {usage}")

            f.seek(0)
            json.dump(usage, f)
            f.truncate()

    def compute_costs(self):
        """Compute the costs of the models."""
        costs = load_file("costs.yaml")
        self.total_prompt_tokens = costs["total_prompt_tokens"]
        self.total_completion_tokens = costs["total_completion_tokens"]
