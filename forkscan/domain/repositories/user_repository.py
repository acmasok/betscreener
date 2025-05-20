from sqlalchemy import select

from forkscan.infrastructure.database.models import User


class UserRepository:
    def __init__(self, session):
        self.session = session  # ожидаем AsyncSession

    async def get_by_id(self, user_id: int):
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_promo_code(self, promo_code: str):
        result = await self.session.execute(
            select(User).where(User.promo_code == promo_code)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str):
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str, promo_code: str, referrer_id: int = None):
        user = User(
            email=email,
            hashed_password=hashed_password,
            promo_code=promo_code,
            referrer_id=referrer_id
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
