import redis.asyncio as redis
from fastapi import Depends, Request


async def get_redis_client(request: Request) -> redis.Redis:
    """FastAPI Dependency для получения Redis из app.state."""
    redis_client = request.app.state.redis
    if not redis_client:
        raise RuntimeError("Redis connection not available!")
    return redis_client
