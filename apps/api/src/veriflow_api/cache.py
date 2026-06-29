from redis.asyncio import Redis

from veriflow_api.config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


async def check_redis() -> None:
    """Raise an exception when Redis is unavailable."""

    await redis_client.ping()
