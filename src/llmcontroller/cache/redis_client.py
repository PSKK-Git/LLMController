import redis.asyncio as aioredis

from llmcontroller.config import settings


def get_redis() -> aioredis.Redis:
    """Async Redis client. decode_responses keeps values as str, not bytes."""
    return aioredis.from_url(settings.redis_url, decode_responses=True)
