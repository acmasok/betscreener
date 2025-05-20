from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from forkscan.api.schemas.models import UserOut, UserRegister, UserLogin
from forkscan.core.config import settings
from forkscan.domain.repositories.user_repository import UserRepository
from forkscan.infrastructure.database.session import get_db
from forkscan.services.auth import create_access_token
from forkscan.services.user import register_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_auth_service() -> AuthService:
    # внедрение зависимости user_repo
    ...

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserOut)
def register(user: UserRegister, session: AsyncSession = Depends(get_db)):
    repo = UserRepository(session)
    try:
        user_obj = register_user(
            repo,
            str(user.email),
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
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user_obj = await repo.get_by_email(str(user.email))
    if not user_obj or not verify_password(user.password, user_obj.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user_obj.id)})
    return {"access_token": token, "token_type": "bearer"}
