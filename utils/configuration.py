from pydantic import BaseModel

from razzler_brain.razzler import RazzlerBrainConfig
from signal_interface.dataclasses import SignalCredentials

from .mongo import MongoConfig
from .redis import RedisCredentials


class GeneralConfig(BaseModel):
    num_producers: int = 1
    num_consumers: int = 1
    num_brains: int = 1
    debug: bool = False
    jwt_secret: str


class Config(BaseModel):
    signal: SignalCredentials
    redis: RedisCredentials
    rabbitmq: dict
    razzler_brain: RazzlerBrainConfig
    general: GeneralConfig
    mongodb: MongoConfig
