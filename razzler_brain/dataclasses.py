from typing import List

from pydantic import BaseModel


class RazzlerBrainConfig(BaseModel):
    commands: List[str]
    admins: List[str]
    razzler_phone_number: str
