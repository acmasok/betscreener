from pydantic import BaseModel, EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str