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
from utils.storage import RedisCredentials

basicConfig(level=INFO)
logger = getLogger(__name__)


class GeneralConfig(BaseModel):
    num_producers: int = 1
    num_consumers: int = 1
    num_brains: int = 1


def main(
    signal_login: SignalCredentials,
    rabbit_config: dict,
    redis_config: RedisCredentials,
    brain_config: RazzlerBrainConfig,
    general_config: GeneralConfig,
):
    logger.info("Starting up a Razzler...")

    producers: List[SignalProducer] = []
    for _ in range(general_config.num_producers):
        producer = SignalProducer(signal_login, rabbit_config)
        producers.append(producer)

    consumers: List[SignalConsumer] = []
    for _ in range(general_config.num_consumers):
        consumer = SignalConsumer(signal_login, redis_config, rabbit_config)
        consumers.append(consumer)

    brains: List[RazzlerBrain] = []
    for _ in range(general_config.num_brains):
        brain = RazzlerBrain(
            redis_config,
            rabbit_config,
            brain_config,
        )
        brains.append(brain)

    if general_config.num_producers:
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
    config_fname = "config.yaml"

    with open(config_fname, "r") as f:
        config = yaml.safe_load(f)

    # Load the signal configuration
    signal_login = SignalCredentials(**config["signal"])
    logger.info("Signal login information loaded.")

    # Redis is easy
    redis_config = RedisCredentials(**config["redis"])

    # Connect to rabbit
    rabbit_config = config["rabbitmq"]

    # Load the brain configuration
    brain_config = RazzlerBrainConfig(**config["razzler_brain"])

    # Load the general configuration (runners)
    general_config = GeneralConfig(**config["general"])

    main(
        signal_login, rabbit_config, redis_config, brain_config, general_config
    )
