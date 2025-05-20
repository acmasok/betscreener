from typing import Optional

from pydantic import BaseModel, EmailStr, constr

class UserRegister(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=6, max_length=128)
    promo_code: Optional[str] = None  # <-- добавили тут

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    promo_code: str  # показываем пользователю его промокод

class PromoCodeUpdate(BaseModel):
    new_promo_code: constr(min_length=4, max_length=20)
