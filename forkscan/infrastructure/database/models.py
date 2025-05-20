from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    promo_code = Column(String, unique=True, nullable=False)  # теперь обязательное и уникальное поле

    __table_args__ = (
        UniqueConstraint('promo_code', name='uq_user_promo_code'),
    )