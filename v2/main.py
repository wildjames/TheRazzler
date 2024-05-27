import threading
from logging import INFO, basicConfig, getLogger

import pika
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
    rabbit_config: pika.ConnectionParameters,
    redis_config: RedisCredentials,
    brain_config: RazzlerBrainConfig,
    general_config: GeneralConfig,
):
    logger.info("Starting up a Razzler...")

    producers = []
    for _ in range(general_config.num_producers):
        producer = SignalProducer(signal_login, rabbit_config)
        producers.append(producer)

    consumers = []
    for _ in range(general_config.num_consumers):
        consumer = SignalConsumer(signal_login, redis_config, rabbit_config)
        consumers.append(consumer)

    brains = []
    for _ in range(general_config.num_brains):
        brain = RazzlerBrain(
            redis_config,
            rabbit_config,
            brain_config,
        )
        brains.append(brain)

    admin_message(producers[0], "Starting the Razzler")

    producer_threads = [
        threading.Thread(target=producer.start, daemon=True, name="producer")
        for producer in producers
    ]
    consumer_threads = [
        threading.Thread(target=consumer.start, daemon=True, name="consumer")
        for consumer in consumers
    ]
    brain_threads = [
        threading.Thread(target=brain.start, daemon=True, name="brain")
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
    if "credentials" in rabbit_config:
        rabbit_config["credentials"] = pika.PlainCredentials(
            **rabbit_config["credentials"]
        )
    rabbit_config = pika.ConnectionParameters(**rabbit_config)

    # Load the brain configuration
    brain_config = RazzlerBrainConfig(**config["razzler_brain"])

    # Load the general configuration (runners)
    general_config = GeneralConfig(**config["general"])

    main(
        signal_login, rabbit_config, redis_config, brain_config, general_config
    )
