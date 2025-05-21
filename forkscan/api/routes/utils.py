from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forkscan.infrastructure.database.models import User
from forkscan.infrastructure.database.session import get_db


async def check_promocode(code: str, session: AsyncSession = Depends(get_db)):
    """
    Проверяет валидность промокода.
    Возвращает информацию о реферере, если промокод валиден.
    """
    res = await session.execute(select(User).where(User.promo_code == code))
    referrer = res.scalar_one_or_none()
    if not referrer:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    # Можно вернуть что угодно, например только id или email
    return {
        "valid": True,
        "referrer_id": referrer.id,
    }
