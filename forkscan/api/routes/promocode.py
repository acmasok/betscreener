from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forkscan.api.schemas.models import PromoCodeUpdate
from forkscan.api.schemas.models import UserResponse
from forkscan.domain.repositories.user_repository import UserRepository

from forkscan.infrastructure.database.session import get_db
from forkscan.api.routes.utils import check_promocode
router = APIRouter(prefix="/promocode", tags=["promocode"])


@router.get("/check_promocode")
async def check_promocode_req(code: str, session: AsyncSession = Depends(get_db)):
    """
    Проверяет валидность промокода.
    Возвращает информацию о реферере, если промокод валиден.
    """
    return await check_promocode(code, session=session)


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
