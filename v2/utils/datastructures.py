from pydantic import BaseModel
from razzler_brain.razzler import RazzlerBrainConfig
from signal_interface.signal_data_classes import SignalCredentials
from utils.storage import RedisCredentials


class GeneralConfig(BaseModel):
    num_producers: int = 1
    num_consumers: int = 1
    num_brains: int = 1


class Config(BaseModel):
    signal: SignalCredentials
    redis: RedisCredentials
    rabbitmq: dict
    razzler_brain: RazzlerBrainConfig
    general: GeneralConfig
