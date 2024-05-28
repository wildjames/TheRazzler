import asyncio
import threading
from logging import INFO, basicConfig, getLogger
from typing import List

import yaml
from pydantic import BaseModel
from razzler_brain.razzler import RazzlerBrain, RazzlerBrainConfig
from signal_interface.signal_consumer import SignalConsumer
from signal_interface.signal_data_classes import SignalCredentials
from signal_interface.signal_producer import SignalProducer, admin_message
from utils.storage import RedisCredentials, load_file

basicConfig(level=INFO)
logger = getLogger(__name__)


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


def main(config: Config):
    logger.info("Starting up a Razzler...")

    producers: List[SignalProducer] = []
    for _ in range(config.general.num_producers):
        producer = SignalProducer(config.signal, config.rabbitmq, config.redis)
        producers.append(producer)

    consumers: List[SignalConsumer] = []
    for _ in range(config.general.num_consumers):
        consumer = SignalConsumer(config.signal, config.redis, config.rabbitmq)
        consumers.append(consumer)

    brains: List[RazzlerBrain] = []
    for _ in range(config.general.num_brains):
        brain = RazzlerBrain(
            config.redis,
            config.rabbitmq,
            config.razzler_brain,
        )
        brains.append(brain)

    if config.general.num_producers:
        asyncio.run(admin_message(producers[0], "Starting the Razzler"))

    producer_threads = [
        threading.Thread(
            target=asyncio.run,
            args=(producer.start(),),
            daemon=True,
        )
        for producer in producers
    ]
    # Consumer start methods are async
    consumer_threads = [
        threading.Thread(
            target=asyncio.run,
            args=(consumer.start(),),
            daemon=True,
        )
        for consumer in consumers
    ]
    brain_threads = [
        threading.Thread(
            target=asyncio.run,
            args=(brain.start(),),
            daemon=True,
        )
        for brain in brains
    ]

    for thread in producer_threads:
        thread.start()
    for thread in consumer_threads:
        thread.start()
    for thread in brain_threads:
        thread.start()

    for thread in producer_threads:
        thread.join()
    for thread in consumer_threads:
        thread.join()
    for thread in brain_threads:
        thread.join()


if __name__ in "__main__":
    # Load the configuration from the data directory
    config = yaml.safe_load(load_file("config.yaml"))
    config = Config(**config)

    main(config)
