from contextlib import asynccontextmanager

from fastapi import FastAPI

from forkscan.api.routes.auth import router as auth_router
from forkscan.api.routes.promocode import router as promocode_router
from forkscan.infrastructure.redis_client import get_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Подключаемся к Redis при старте приложения
    redis_client = await get_redis()
    app.state.redis = redis_client  # Сохраняем в app.state
    yield
    # Закрываем соединение при остановке
    await close_redis(redis_client)


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router, prefix="/auth")
app.include_router(promocode_router, prefix="/promocode")
