from typing import Dict, Union

from pydantic import BaseModel, Field


class OpenAIConfig(BaseModel):
    fast_model: str = "gpt-3.5-turbo"
    quality_model: str = "gpt-3.5-turbo"
    vision_model: str = "gpt-4o"
    image_model: str = "dall-e-3"
    chat_completion_kwargs: Dict[str, Union[str, int, float]] = Field(
        default_factory=dict
    )
    vision_completion_kwargs: Dict[str, Union[str, int, float]] = Field(
        default_factory=dict
    )
    image_generation_kwargs: Dict[str, Union[str, int, float]] = Field(
        default_factory=dict
    )


IMAGE_TOKENS = {
    "256x256": 755,
}
