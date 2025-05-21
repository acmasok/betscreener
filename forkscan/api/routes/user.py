# api/routes/user.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from forkscan.api.routes.auth import get_current_user
from forkscan.api.schemas.models import PromoCodeUpdate, UserOut
from forkscan.domain.repositories.user_repository import UserRepository
from forkscan.infrastructure.database.session import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/change_promocode", response_model=UserOut)
async def update_promo_code(
    body: PromoCodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
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
