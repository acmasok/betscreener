from passlib.context import CryptContext
from forkscan.domain.repositories.user_repository import UserRepository
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, email: str, password: str, promokode: str | None = None):
        if await self.user_repo.get_by_email(email):
            raise ValueError("Email уже занят")
        promokode_obj = None
        if promokode:
            promokode_obj = await self.user_repo.get_by_promo_code(promokode)
            if not promokode_obj:
                raise ValueError("Промокод не найден")
        hashed_password = pwd_context.hash(password)
        user = await self.user_repo.create({
            "email": email,
            "hashed_password": hashed_password,
            "promokode": promokode_obj["id"] if promokode_obj else None
        })
        return user

    async def login(self, email: str, password: str):
        user = await self.user_repo.get_by_email(email)
        if not user or not pwd_context.verify(password, user.hashed_password):
            raise ValueError("Неверные email или пароль")
        return user