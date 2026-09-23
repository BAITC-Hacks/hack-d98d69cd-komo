import logging
from redis.asyncio import Redis
from redis.exceptions import RedisError
from app.core.config import settings

logger = logging.getLogger(__name__)
cache = Redis.from_url(settings().redis_url, decode_responses=True, socket_connect_timeout=0.15, socket_timeout=0.15)


async def cache_get(key: str) -> str | None:
    try:
        return await cache.get(key)
    except (RedisError, OSError):
        return None


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    try:
        await cache.set(key, value, ex=ttl)
    except (RedisError, OSError):
        pass
