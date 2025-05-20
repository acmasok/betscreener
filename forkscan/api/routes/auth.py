import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from forkscan.api.schemas.models import UserLogin, UserRegister, UserResponse
from forkscan.core.config import settings
from forkscan.infrastructure.database.models import RefreshToken, User
from forkscan.infrastructure.database.session import get_db

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_promo_code(length=6):
    return secrets.token_urlsafe(length)


def create_access_token(
    token_data: dict, secret: str, algorithm: str, expires_delta: timedelta | None = None
):
    to_encode = token_data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expires))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def create_refresh_token(
    user_id: int, email: str, secret: str, algorithm: str, expires_delta: timedelta | None = None
):
    expires = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.jwt_refresh_expires_days)
    )
    jti = str(uuid.uuid4())  # уникальный идентификатор токена
    payload = {"user_id": user_id, "email": email, "exp": expires, "jti": jti, "type": "refresh"}
    refresh_token = jwt.encode(payload, secret, algorithm=algorithm)
    return refresh_token, jti, expires


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


# Регистрация
@router.post("/register", response_model=UserResponse)
async def register(data: UserRegister, session: AsyncSession = Depends(get_db)):
    # Проверка email
    res = await session.execute(select(User).where(User.email == data.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email уже занят")

    # Проверка промокода (если указан)
    referrer_id = None
    if data.promokode:
        res = await session.execute(select(User).where(User.promo_code == data.promokode))
        referrer = res.scalar_one_or_none()
        if not referrer:
            raise HTTPException(status_code=400, detail="Промокод не найден")
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


# Авторизация
@router.post("/login")
async def login(data: UserLogin, session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(User).where(User.email == data.email))
    user = res.scalar_one_or_none()
    if not user or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверные email или пароль")

    # Генерируем JWT (по желанию)
    token_data = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(
        token_data,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.jwt_expires),
    )
    refresh_token, jti, refresh_exp = create_refresh_token(
        user.id, user.email, settings.jwt_secret, settings.jwt_algorithm
    )

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
        max_age=settings.jwt_refresh_expires_days * 60 * 60,
    )
    return response


@router.post("/logout")
async def logout(request: Request, session: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token provided")
    try:
        payload = jwt.decode(
            refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        jti = payload.get("jti")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # Помечаем токен как отозванный
    res = await session.execute(select(RefreshToken).where(RefreshToken.token == jti))
    db_token = res.scalar_one_or_none()
    if db_token:
        db_token.revoked = True
        await session.commit()
    response = JSONResponse({"detail": "Logged out"})
    response.delete_cookie("refresh_token")
    return response
