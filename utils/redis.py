from typing import Optional

import redis
from pydantic import BaseModel


class RedisCredentials(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


def get_redis_client(redis_config: RedisCredentials) -> redis.Redis:
    return redis.Redis(**redis_config.model_dump(), decode_responses=True)
