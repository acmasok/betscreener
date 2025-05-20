import secrets
import uuid
from datetime import datetime, timedelta, UTC

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forkscan.core.config import settings
from forkscan.infrastructure.database.models import User, RefreshToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_promo_code(length=6):
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expires))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int, email: str, expires_delta: timedelta | None = None):
    expires = datetime.now(UTC) + (expires_delta or timedelta(days=settings.jwt_refresh_expires_days))
    jti = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expires,
        "jti": jti,
        "type": "refresh"
    }
    refresh_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return refresh_token, jti, expires


async def save_refresh_token(session: AsyncSession, user_id: int, jti: str):
    db_refresh_token = RefreshToken(
        user_id=user_id,
        token=jti,
        created_at=datetime.now(UTC),
        revoked=False,
    )
    session.add(db_refresh_token)
    await session.commit()


async def revoke_refresh_token(session: AsyncSession, jti: str):
    res = await session.execute(
        select(RefreshToken).where(RefreshToken.token == jti)
    )
    db_token = res.scalar_one_or_none()
    if db_token:
        db_token.revoked = True
        await session.commit()


async def get_user_by_email(session: AsyncSession, email: str):
    res = await session.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int):
    res = await session.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()


async def get_refresh_token(session: AsyncSession, jti: str, user_id: int):
    res = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token == jti,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False
        )
    )
    return res.scalar_one_or_none()

def decode_refresh_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")
    return payload

async def find_valid_refresh_token(session, jti: str, user_id: int):
    res = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token == jti,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
        )
    )
    return res.scalar_one_or_none()