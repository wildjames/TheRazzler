from logging import DEBUG, basicConfig, getLogger
import signal

import yaml
from redis import Redis

from signal_consumer import SignalConsumer, SignalInformation

basicConfig(level=DEBUG)
logger = getLogger(__name__)


def main(signal_login: SignalInformation, redis_conn: Redis):
    logger.info("Starting SignalConsumer...")

    consumer = SignalConsumer(signal_login, redis_conn)

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

    main(signal_login, redis_conn)
