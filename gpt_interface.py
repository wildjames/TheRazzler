import json
import logging
from dataclasses import dataclass
from typing import List, Tuple

import openai
from modelsinfo import COSTS

logger = logging.getLogger(__name__)


def create_chat_message(role, content):
    """
    Create a chat message with the given role and content.

    Args:
    role (str): The role of the message sender, e.g., "system", "user", or "assistant".
    content (str): The content of the message.

    Returns:
    dict: A dictionary containing the role and content of the message.
    """
    return {"role": role, "content": content}


@dataclass
class SignalAI:
    """The SignalAI class, which contains all the logic for the responder AI.

    This class will keep track of the AI's cost, and the user's budget, and will stop when the budget is exceeded.
    """

    model: str = "gpt-3.5-turbo"
    temperature: float = 0.0
    max_tokens: int = 400
    prompt_filename: str = "prompt.txt"

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0
    total_budget: float = 0
    debug: bool = False
    razzler_rate: float = 0.1
    razzler_image_rate: float = 0.1

    def reset(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0
        self.total_budget = 0.0

    def create_chat_completion(
        self,
        messages: list,  # type: ignore
    ) -> str:
        """
        Create a chat completion and update the cost.
        Args:
        messages (list): The list of messages to send to the API.
        model (str): The model to use for the API call.
        temperature (float): The temperature to use for the API call.
        max_tokens (int): The maximum number of tokens for the API call.
        Returns:
        str: The AI's response.
        """
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if self.debug:
            logger.debug(f"[GPTInterface] Response: {response}")
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        self.update_cost(prompt_tokens, completion_tokens, self.model)
        return response

    def create_image_completion(self, text: str) -> str:
        """
        Create an image completion and update the cost.

        Args:
        text (str): The text to send to the API.

        Returns:
        str: The AI's response.
        """
        response = openai.Image.create(
            prompt=text,
            n=1,
            size="1024x1024",
        )
        logger.info(f"[GPTInterface] Response: {response}")
        image_url = response["data"][0]["url"]

        self.total_cost += COSTS["image"]["prompt"]
        logger.info(f"[GPTInterface] Total cost: {self.total_cost}")

        return image_url

    def embedding_create(
        self,
        text_list: List[str],
        model: str = "text-embedding-ada-002",
    ) -> List[float]:
        """
        Create an embedding for the given input text using the specified model.

        Args:
        text_list (List[str]): Input text for which the embedding is to be created.
        model (str, optional): The model to use for generating the embedding.

        Returns:
        List[float]: The generated embedding as a list of float values.
        """
        response = openai.Embedding.create(input=text_list, model=model)

        self.update_cost(response.usage.prompt_tokens, 0, model)
        return response["data"][0]["embedding"]

    def update_cost(self, prompt_tokens, completion_tokens, model):
        """
        Update the total cost, prompt tokens, and completion tokens.

        Args:
        prompt_tokens (int): The number of tokens used in the prompt.
        completion_tokens (int): The number of tokens used in the completion.
        model (str): The model used for the API call.
        """
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost += (
            prompt_tokens * COSTS[model]["prompt"]
            + completion_tokens * COSTS[model]["completion"]
        ) / 1000
        logger.info(f"[GPTInterface] Total running cost: ${self.total_cost:.3f}")

    def set_total_budget(self, total_budget):
        """
        Sets the total user-defined budget for API calls.

        Args:
        prompt_tokens (int): The number of tokens used in the prompt.
        """
        self.total_budget = total_budget

    def get_total_prompt_tokens(self):
        """
        Get the total number of prompt tokens.

        Returns:
        int: The total number of prompt tokens.
        """
        return self.total_prompt_tokens

    def get_total_completion_tokens(self):
        """
        Get the total number of completion tokens.

        Returns:
        int: The total number of completion tokens.
        """
        return self.total_completion_tokens

    def get_total_cost(self):
        """
        Get the total cost of API calls.

        Returns:
        float: The total cost of API calls.
        """
        return self.total_cost

    def get_total_budget(self):
        """
        Get the total user-defined budget for API calls.

        Returns:
        float: The total budget for API calls.
        """
        return self.total_budget
