import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from forkscan.core.config import settings
from forkscan.api.routes.auth.utils import pwd_context, get_ban_time_interval
from forkscan.api.schemas.models import UserRegister, UserResponse
from forkscan.infrastructure.database.models import User
from forkscan.infrastructure.database.session import get_db
from forkscan.services.auth import generate_promo_code
from forkscan.api.deps import get_redis_client

router = APIRouter(prefix="/auth", tags=["auth"])


# Регистрация
@router.post("/register", response_model=UserResponse)
async def register(
    data: UserRegister,
    session: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
    request: Request = None,
):
    # --- Улучшенный лимит регистраций ---
    ip = request.client.host if request else "unknown"
    key = f"register_attempts:{ip}"

    attempts = await redis_client.incr(key)
    if attempts == 1:
        await redis_client.expire(key, 86400)  # 24 часа

    min_attempts = settings.MIN_REGISTER_ATTEMPTS
    max_attempts = settings.MAX_REGISTER_ATTEMPTS

    if attempts > max_attempts:
        ban_time = get_ban_time_interval(attempts, min_attempts)
        remaining = await redis_client.ttl(key)
        if remaining > 0 and remaining < ban_time:
            await redis_client.expire(key, ban_time)
        # logging.warning(f"Banned registration from {ip} for {ban_time} seconds")
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Try again after {remaining} seconds." if remaining > 0 else "Too many attempts. Try it later."
        )
    # --- конец лимита ---

    # Проверка email
    res = await session.execute(select(User).where(User.email == data.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email is already busy")

    # Проверка промокода (если указан)
    referrer_id = None
    if data.promokode:
        res = await session.execute(select(User).where(User.promo_code == data.promokode))
        referrer = res.scalar_one_or_none()
        if not referrer:
            raise HTTPException(status_code=400, detail="The promotional code was not found")
        referrer_id = referrer.id

    # Генерируем свой промокод
    my_promo_code = generate_promo_code()

    # Хешируем пароль
    hashed_pw = pwd_context.hash(data.password)

    user = User(
        email=str(data.email),
        hashed_password=hashed_pw,
        promo_code=my_promo_code,
        referrer_id=referrer_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResponse(
        id=user.id, email=data.email, promo_code=my_promo_code, referrer_id=referrer_id
    )
