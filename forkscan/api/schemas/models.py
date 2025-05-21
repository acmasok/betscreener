from pydantic import BaseModel, EmailStr, constr, field_validator


class UserRegister(BaseModel):
    email: str
    password: str
    promokode: str | None = None

    @field_validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Пароль должен быть не короче 8 символов")
        if v.isdigit() or v.isalpha():
            raise ValueError("Пароль должен содержать буквы и цифры")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    promo_code: str
    referrer_id: int | None = None


class PromoCodeUpdate(BaseModel):
    new_promo_code: constr(min_length=4, max_length=10)
