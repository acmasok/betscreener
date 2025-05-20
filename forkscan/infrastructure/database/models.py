from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    promo_code = Column(String, unique=True, nullable=True)  # Лучше сделать nullable=True
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    referrer = relationship("User", remote_side=[id])  # позволяет удобно получить пригласившего

    # можно добавить для удобства обратную связь
    referrals = relationship("User", backref="invited_by", foreign_keys=[referrer_id])
