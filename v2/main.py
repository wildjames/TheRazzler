from logging import DEBUG, INFO, basicConfig, getLogger

import pika
import yaml
import threading
from redis import Redis

from signal_interface.signal_consumer import SignalConsumer
from signal_interface.signal_data_classes import SignalInformation
from signal_interface.signal_producer import SignalProducer

basicConfig(level=INFO)
logger = getLogger(__name__)


def main(
    signal_login: SignalInformation,
    rabbit_config: pika.ConnectionParameters,
    num_producers: int = 1,
    num_consumers: int = 1,
):
    logger.info("Starting up a Razzler...")

    producers = []
    consumers = []

    for _ in range(num_producers):
        producer = SignalProducer(signal_login, rabbit_config)
        producers.append(producer)
    for _ in range(num_consumers):
        consumer = SignalConsumer(signal_login, rabbit_config)
        consumers.append(consumer)

    producer_threads = [
        threading.Thread(target=producer.start, daemon=True, name="producer")
        for producer in producers
    ]
    consumer_threads = [
        threading.Thread(target=consumer.start, daemon=True, name="consumer")
        for consumer in consumers
    ]

    for thread in producer_threads:
        thread.start()
    for thread in consumer_threads:
        thread.start()

    for thread in producer_threads:
        thread.join()
    for thread in consumer_threads:
        thread.join()


if __name__ == "__main__":
    config_fname = "config.yaml"

    with open(config_fname, "r") as f:
        config = yaml.safe_load(f)

    signal_login = SignalInformation(**config["signal"])
    logger.info(f"Signal login information loaded.")

    redis_conn = Redis(**config["redis"])
    if not redis_conn.ping():
        logger.error(f"Failed to connect to Redis!")
        exit(1)
    logger.info(f"Successfully connected to Redis!")

    # Connect to rabbit
    rabbit_config = config["rabbitmq"]
    if "credentials" in rabbit_config:
        rabbit_config["credentials"] = pika.PlainCredentials(
            **rabbit_config["credentials"]
        )
    rabbit_config = pika.ConnectionParameters(**rabbit_config)

    main(signal_login, rabbit_config)
