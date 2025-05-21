from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from forkscan.core.config import settings
from forkscan.infrastructure.database.models import RefreshToken
from forkscan.infrastructure.database.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/logout")
async def logout(request: Request, session: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token provided")
    try:
        payload = jwt.decode(
            refresh_token, settings.jwt_secret_value, algorithms=[settings.jwt_algorithm]
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
