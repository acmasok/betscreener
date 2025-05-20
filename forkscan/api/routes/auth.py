from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from forkscan.api.schemas.models import UserOut, UserRegister, UserLogin
from forkscan.domain.repositories.user_repository import UserRepository
from forkscan.infrastructure.database.session import get_db
from forkscan.services.auth import create_access_token
from forkscan.services.user import register_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(user: UserRegister, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    try:
        user_obj = register_user(
            repo,
            str(user.email),
            user.username,
            user.password,
            user.promo_code  # это реферальный код (referrer)
        )
        return UserOut(
            id=user_obj.id,
            email=user_obj.email,
            username=user_obj.username,
            promo_code=user_obj.promo_code
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user_obj = repo.get_by_email(str(user.email))
    if not user_obj or not verify_password(user.password, user_obj.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user_obj.id)})
    return {"access_token": token, "token_type": "bearer"}
