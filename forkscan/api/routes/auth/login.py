from datetime import UTC, datetime, timedelta

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from forkscan.api.deps import get_redis_client
from forkscan.api.routes.auth.utils import get_ban_time, pwd_context
from forkscan.api.schemas.models import UserLogin
from forkscan.core.config import settings
from forkscan.infrastructure.database.models import RefreshToken, User
from forkscan.infrastructure.database.session import get_db
from forkscan.services.auth import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


# Авторизация
@router.post("/login")
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_db),
    request: Request = None,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    # Получаем IP пользователя (можно сделать по email, но IP лучше для защиты)
    ip = request.client.host
    key = f"login_fail:{ip}"

    # 1. Проверяем, есть ли бан
    fail_count = await redis_client.get(key)
    if fail_count and int(fail_count) >= settings.max_failed_attempts:
        raise HTTPException(status_code=429, detail="Too many attempts. Try it later.")

    # 2. Ищем пользователя
    res = await session.execute(select(User).where(User.email == data.email))
    user = res.scalar_one_or_none()
    if not user or not pwd_context.verify(data.password, user.hashed_password):
        # 3. Неудачная попытка: увеличиваем счетчик
        fails = await redis_client.incr(key)
        if fails == 1:
            ban_time = get_ban_time(fails)
            await redis_client.expire(key, ban_time)
        raise HTTPException(status_code=400, detail="Inappropriate email or password")

    # 4. Успешная попытка: сбрасываем счетчик
    await redis_client.delete(key)

    # Генерируем JWT (по желанию)
    token_data = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(
        token_data,
        expires_delta=timedelta(minutes=settings.jwt_expires),
    )
    refresh_token, jti, refresh_exp = create_refresh_token(user.id, user.email)

    # Сохраняем refresh_token (или jti) в базе
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token=jti,  # сохраняем только jti, а не весь jwt
        created_at=datetime.now(UTC),
        revoked=False,
    )
    session.add(db_refresh_token)
    await session.commit()

    # Кладём refresh_token в httpOnly cookie
    response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # только по https!
        samesite="strict",
        max_age=settings.jwt_refresh_expires_days * 60 * 60 * 24,
    )
    return response
