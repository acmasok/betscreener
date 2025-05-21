from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forkscan.api.schemas.models import PromoCodeUpdate
from forkscan.api.schemas.models import UserResponse
from forkscan.domain.repositories.user_repository import UserRepository
from forkscan.infrastructure.database.models import User
from forkscan.infrastructure.database.session import get_db

router = APIRouter(prefix="/promocode", tags=["promocode"])


@router.get("/check_promocode")
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
        "referrer_email": referrer.email,
    }


@router.patch("/change_promocode", response_model=UserResponse)
async def update_promo_code(
        body: PromoCodeUpdate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(UserResponse),
):
    repo = UserRepository(db)
    # Проверяем, не занят ли промокод
    existing = await repo.get_by_promo_code(body.new_promo_code)
    if existing:
        raise HTTPException(status_code=400, detail="Promo code already taken")
    # Меняем промокод
    current_user.promo_code = body.new_promo_code
    await db.commit()
    await db.refresh(current_user)
    return current_user
