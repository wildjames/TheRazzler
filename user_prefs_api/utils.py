import random
from logging import getLogger

import aio_pika

from signal_interface.dataclasses import OutgoingMessage
from utils.local_storage import load_phonebook
from utils.redis import RedisCredentials, get_redis_client

logger = getLogger(__name__)


def get_otp(user_phone_number: str, redis_config: RedisCredentials, expiry=60):
    phonebook = load_phonebook()

    contact = phonebook.get_contact(user_phone_number)
    if not contact:
        raise ValueError(
            f"Contact with phone number {user_phone_number} not found"
        )
    logger.info(f"Generating OTP for {contact.uuid}")

    chars = "0123456789"

    otp = "".join(random.choices(chars, k=6))

    redis = get_redis_client(redis_config)
    redis.set(f"razzler_otp:{contact.uuid}", otp, ex=expiry)

    return otp


def fetch_cached_otp(user_phone_number: str, redis_config: RedisCredentials):
    phonebook = load_phonebook()

    contact = phonebook.get_contact(user_phone_number)
    logger.info(f"Checking OTP for {contact.uuid}")

    client = get_redis_client(redis_config)
    stored_otp = client.get(f"razzler_otp:{contact.uuid}")

    if stored_otp:
        # Delete it from the cache, now it's used
        client.delete(f"razzler_otp:{contact.uuid}")

    return stored_otp


async def publish_message(message: OutgoingMessage, rabbit_config: dict):
    conn = await aio_pika.connect_robust(**rabbit_config)

    async with conn as connection:
        channel = await connection.channel()

        # Publish the outgoing message to the queue
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=message.model_dump_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="outgoing_messages",
        )

    await conn.close()
