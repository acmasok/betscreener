from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from forkscan.api.routes.auth.utils import pwd_context
from forkscan.api.schemas.models import UserLogin
from forkscan.api.security_system import get_security_system
from forkscan.core.config import settings
from forkscan.infrastructure.database.models import RefreshToken, User
from forkscan.infrastructure.database.session import get_db
from forkscan.services.auth import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


# Авторизация
@router.post("/login")
async def login(
    data: UserLogin,
    captcha_response: str = Form(...),
    session: AsyncSession = Depends(get_db),
    request: Request = None,
    security=Depends(get_security_system),
):
    """
    User login endpoint with security checks

    Args:
        data: Login credentials
        captcha_response: CAPTCHA verification token
        session: Database session
        request: FastAPI request object
        security: Security system instance

    Returns:
        JSONResponse with access token

    Raises:
        HTTPException: If security checks fail or invalid credentials
    """
    # Получаем IP пользователя
    ip = request.client.host

    # Проверяем безопасность
    security_result = await security.handle_login_attempt(ip, captcha_response)

    if not security_result.success:
        error_detail = {
            "message": security_result.message,
            "remaining_attempts": security_result.remaining_attempts,
        }
        raise HTTPException(
            status_code=429 if security_result.is_banned else 400, detail=error_detail
        )

    try:
        # Ищем пользователя
        res = await session.execute(select(User).where(User.email == data.email))
        user = res.scalar_one_or_none()

        # Проверяем учетные данные
        if not user or not pwd_context.verify(data.password, user.hashed_password):
            # При неудачной попытке НЕ сбрасываем security_result
            raise HTTPException(status_code=400, detail="Invalid email or password")

        # При успешном входе сбрасываем все ограничения
        await security.reset_attempts(ip)

        # Генерируем токены
        token_data = {"user_id": user.id, "email": user.email}
        access_token = create_access_token(
            token_data,
            expires_delta=timedelta(minutes=settings.jwt_expires),
        )
        refresh_token, jti, refresh_exp = create_refresh_token(user.id, user.email)

        # Сохраняем refresh token
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token=jti,
            created_at=datetime.now(UTC),
            revoked=False,
        )
        session.add(db_refresh_token)
        await session.commit()

        # Формируем ответ
        response = JSONResponse(
            {"access_token": access_token, "token_type": "bearer", "message": "Login successful"}
        )

        # Устанавливаем cookie с refresh token
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=settings.jwt_refresh_expires_days * 60 * 60 * 24,
        )

        return response

    except HTTPException:
        # Пробрасываем HTTP исключения дальше
        raise

    except Exception as e:
        # Логируем неожиданные ошибки
        security.logger.error(f"Login error for {ip}: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during login")
