import signal
from logging import DEBUG, INFO, basicConfig, getLogger

import pika
import yaml
from redis import Redis
from signal_consumer import SignalConsumer
from signal_data_classes import SignalInformation
from signal_producer import SignalProducer

basicConfig(level=INFO)
logger = getLogger(__name__)


def main(
    signal_login: SignalInformation,
    rabbit_config: pika.ConnectionParameters,
):
    logger.info("Starting SignalConsumer...")

    consumer = SignalConsumer(signal_login, rabbit_config)
    producer = SignalProducer(signal_login, rabbit_config)

    # Catch kill signal (CTRL+C) and stop the consumer
    def signal_handler(sig, frame):
        consumer.stop()
        logger.info("SignalConsumer stopped.")
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    consumer.start()

    logger.info("SignalConsumer stopped.")


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
