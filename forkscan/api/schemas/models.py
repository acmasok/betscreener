from pydantic import BaseModel, EmailStr, constr


class UserRegister(BaseModel):
    email: EmailStr
    password: constr(min_length=6, max_length=25)
    promokode: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    promo_code: str  # показываем пользователю его промокод


class PromoCodeUpdate(BaseModel):
    new_promo_code: constr(min_length=4, max_length=10)
