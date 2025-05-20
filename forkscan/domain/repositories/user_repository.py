from forkscan.infrastructure.database.models import User
from sqlalchemy.orm import Session

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_promo_code(self, promo_code: str):
        return self.db.query(User).filter(User.promo_code == promo_code).first()

    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def create(self, email: str, username: str, hashed_password: str, promo_code: str, referrer_code: str = None):
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            promo_code=promo_code,
        )
        # Можно связать с реферером, если referrer_code указан (например, добавить связь в таблице)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user