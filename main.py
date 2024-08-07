import asyncio
import multiprocessing
import os
from logging import INFO, DEBUG, basicConfig, getLogger
import signal
import sys
from typing import List

import yaml

from razzler_brain.razzler import RazzlerBrain
from signal_interface.signal_consumer import SignalConsumer
from signal_interface.signal_producer import SignalProducer
from utils.configuration import Config
from utils.local_storage import load_file


# Load the configuration from the data directory
config = yaml.safe_load(load_file("config.yaml"))
config = Config(**config)

if config.general.debug:
    basicConfig(level=DEBUG)
else:
    basicConfig(level=INFO)

logger = getLogger(__name__)


def run_asyncio_coroutine(coroutine_func, *args):
    asyncio.run(coroutine_func(*args))


def main(config: Config):
    logger.info("Starting up Razzler components in separate processes...")

    # Initialize producers
    producers: List[SignalProducer] = [
        SignalProducer(
            config.signal,
            config.rabbitmq,
            config.redis,
        )
        for _ in range(config.general.num_producers)
    ]

    # Initialize consumers
    consumers: List[SignalConsumer] = [
        SignalConsumer(
            config.signal,
            config.redis,
            config.rabbitmq,
        )
        for _ in range(config.general.num_consumers)
    ]

    # Initialize brains
    brains: List[RazzlerBrain] = [
        RazzlerBrain(
            config.redis,
            config.rabbitmq,
            config.mongodb,
            config.razzler_brain,
        )
        for _ in range(config.general.num_brains)
    ]

    # Create processes for producers
    producer_processes = [
        multiprocessing.Process(
            target=run_asyncio_coroutine, args=(producer.start,)
        )
        for producer in producers
    ]

    # Create processes for consumers
    consumer_processes = [
        multiprocessing.Process(
            target=run_asyncio_coroutine, args=(consumer.start,)
        )
        for consumer in consumers
    ]

    # Create processes for brains
    brain_processes = [
        multiprocessing.Process(
            target=run_asyncio_coroutine, args=(brain.start,)
        )
        for brain in brains
    ]

    # Start all processes
    for process in producer_processes + consumer_processes + brain_processes:
        process.start()

    # Wait for all processes to complete
    for process in producer_processes + consumer_processes + brain_processes:
        process.join()


def shutdown_handler(signum, frame):
    # You would add any necessary cleanup here
    logger.info("Shutdown signal received. Cleaning up...")
    # Optionally, send a stop or close signal to your asyncio coroutines
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

if __name__ == "__main__":
    # Check that the OPENAI_API_KEY environment variable is set
    if "OPENAI_API_KEY" not in os.environ:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    if "DATA_DIR" not in os.environ:
        logger.warn(
            "DATA_DIR environment variable not set. Using default value."
        )

    main(config)
