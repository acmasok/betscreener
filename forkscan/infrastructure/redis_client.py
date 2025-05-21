import redis.asyncio as redis

from forkscan.core.config import settings


async def get_redis() -> redis.Redis:
    """Создаёт и возвращает подключение к Redis."""
    return redis.Redis.from_url(
        str(settings.redis_url),
        decode_responses=True,
        encoding="utf-8",
    )


async def close_redis(client: redis.Redis) -> None:
    """Корректно закрывает соединение с Redis."""
    if client is not None:
        await client.aclose()  # aclose() для асинхронного закрытия
