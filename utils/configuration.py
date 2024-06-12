from pydantic import BaseModel

from razzler_brain.razzler import RazzlerBrainConfig
from signal_interface.dataclasses import SignalCredentials

from .local_storage import RedisCredentials
from .mongo import MongoConfig


class GeneralConfig(BaseModel):
    num_producers: int = 1
    num_consumers: int = 1
    num_brains: int = 1
    debug: bool = False


class Config(BaseModel):
    signal: SignalCredentials
    redis: RedisCredentials
    rabbitmq: dict
    razzler_brain: RazzlerBrainConfig
    general: GeneralConfig
    mongodb: MongoConfig
