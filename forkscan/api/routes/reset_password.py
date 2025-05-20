from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forkscan.api.schemas.reset_password import ResetPasswordConfirm, ResetPasswordRequest
from forkscan.core.config import settings
from forkscan.infrastructure.database.models import User
from forkscan.infrastructure.database.session import get_db

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 1. Запрос на сброс пароля
@router.post("/forgot-password")
async def forgot_password(data: ResetPasswordRequest, session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(User).where(User.email == data.email))
    user = res.scalar_one_or_none()
    if not user:
        # Не раскрываем, есть ли пользователь
        return {"msg": "Если email есть в системе, на него придёт письмо для сброса пароля."}

    token_data = {
        "user_id": user.id,
        "email": user.email,
        "exp": datetime.now(UTC) + timedelta(hours=1),  # токен живет 1 час
        "type": "reset",
    }
    reset_token = jwt.encode(token_data, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"

    # === Здесь отправь письмо! ===
    # send_email(user.email, reset_link)
    print("Ссылка для сброса пароля:", reset_link)  # для дебага

    return {"msg": "Если email есть в системе, на него придёт письмо для сброса пароля."}


# 2. Подтверждение сброса пароля
@router.post("/reset-password")
async def reset_password(data: ResetPasswordConfirm, session: AsyncSession = Depends(get_db)):
    # Валидация токена
    try:
        payload = jwt.decode(data.token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = payload.get("user_id")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Меняем пароль
    res = await session.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = pwd_context.hash(data.new_password)
    await session.commit()

    return {"msg": "Пароль успешно изменён"}
