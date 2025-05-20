from datetime import timedelta

from fastapi import Request, Depends, HTTPException, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from forkscan.core.config import settings
from forkscan.infrastructure.database.session import get_db
from forkscan.services.auth import create_access_token, decode_refresh_token, find_valid_refresh_token

router = APIRouter()


# Обновляем токен
@router.post("/refresh")
async def refresh_token(request: Request, session: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    # Вынесли декодирование и валидацию в сервис
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    jti = payload["jti"]
    user_id = payload["user_id"]

    db_token = await find_valid_refresh_token(session, jti, user_id)
    if not db_token:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found")

    access_token = create_access_token(
        {"user_id": user_id, "email": payload.get("email")},
        expires_delta=timedelta(minutes=settings.jwt_expires),
    )
    return {"access_token": access_token, "token_type": "bearer"}
