from datetime import timedelta

from fastapi import Request, Depends, HTTPException, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from forkscan.core.config import settings
from forkscan.infrastructure.database.models import RefreshToken
from forkscan.infrastructure.database.session import get_db
from forkscan.services.auth import create_access_token

router = APIRouter()


# Обновляем токен
@router.post("/refresh")
async def refresh_token(request: Request, session: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    try:
        payload = jwt.decode(
            refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        jti = payload.get("jti")
        user_id = payload.get("user_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Проверка: есть ли такой токен в базе, не отозван ли он
    res = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token == jti,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
        )
    )
    db_token = res.scalar_one_or_none()
    if not db_token:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found")

    # Всё ок — выдаём новый access_token
    access_token = create_access_token(
        {"user_id": user_id, "email": payload.get("email")},
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.jwt_expires),
    )
    return {"access_token": access_token, "token_type": "bearer"}
