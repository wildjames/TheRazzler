import json
import random
import re
from logging import getLogger
from typing import Dict, List, Union

import openai
from openai.resources.chat.completions import ChatCompletionMessageParam
from openai.types.chat.chat_completion import Choice, ChatCompletion
from pydantic import BaseModel, Field
import yaml
from utils.storage import load_file, load_file_lock, save_file

logger = getLogger(__name__)


def clean_filename(filename):
    # Replaces non-alphanumeric characters (except for periods, hyphens and underscores) with an underscore
    filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    # Replaces any remaining forward slashes with an underscore
    filename = filename.replace("/", "_")
    return filename


class OpenAIConfig(BaseModel):
    fast_model: str = "gpt-3.5-turbo"
    quality_model: str = "gpt-3.5-turbo"
    chat_completion_kwargs: Dict[str, Union[str, int]] = Field(
        default_factory=dict
    )


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

    def create_chat_completion(
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

        response: ChatCompletion = self.llm.chat.completions.create(
            model=use_model,
            messages=messages,
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
        role (str): The role of the message sender, e.g., "system", "user", or "assistant".
        content (str): The content of the message.

        Returns:
        dict: A dictionary containing the role and content of the message.
        """
        return {"role": role, "content": content}

    def update_costs(self, response: ChatCompletion):
        """Update the costs of the models."""
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

            json.dump(usage, f)

    def compute_costs(self):
        """Compute the costs of the models."""
        costs = load_file("costs.yaml")
        self.total_prompt_tokens = costs["total_prompt_tokens"]
        self.total_completion_tokens = costs["total_completion_tokens"]
