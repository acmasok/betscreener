from datetime import UTC, datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    promo_code: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    referrer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))

    referrer: Mapped[Optional["User"]] = relationship(
        remote_side=[id], foreign_keys=[referrer_id], back_populates="referrals"
    )

    referrals: Mapped[List["User"]] = relationship(back_populates="referrer")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # jti или сам JWT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
