import secrets
import string

from passlib.context import CryptContext

from forkscan.domain.repositories.user_repository import UserRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def register_user(user_repo: UserRepository, email: str, password: str, promo_code: str = None):
    if user_repo.get_by_email(email):
        raise ValueError("Email already registered")
    hashed_pwd = hash_password(password)
    return user_repo.create(email, hashed_pwd, promo_code)

def generate_promo_code(length=5):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))
