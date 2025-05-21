from fastapi import Request, Depends
import redis.asyncio as redis

async def get_redis_client(request: Request) -> redis.Redis:
    """FastAPI Dependency для получения Redis из app.state."""
    redis_client = request.app.state.redis
    if not redis_client:
        raise RuntimeError("Redis connection not available!")
    return redis_client