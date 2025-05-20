from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forkscan.api.routes.auth.utils import pwd_context
from forkscan.api.schemas.models import UserRegister, UserResponse
from forkscan.infrastructure.database.models import User
from forkscan.infrastructure.database.session import get_db
from forkscan.services.auth import generate_promo_code

router = APIRouter()


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
