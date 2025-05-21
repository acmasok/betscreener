from datetime import UTC, datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from forkscan.infrastructure.database.base import Base


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
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="user"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # jti или сам JWT
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)  # <--- вот так!
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    # subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )  # 'basic', 'pro', 'enterprise'
    name: Mapped[str] = mapped_column(String, nullable=False)  # отображаемое имя
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)  # цена за месяц/период
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)  # длительность (например, 30)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscription_plans.id"), nullable=False
    )
    start_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="subscriptions")
