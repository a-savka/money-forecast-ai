from datetime import date

from sqlalchemy import Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    # Ключ демо-профиля синтетических данных (young/family/freelancer/dropout)
    profile: Mapped[str | None] = mapped_column(String(32))
    # MOCK: в реальной версии статус подписки приходит из платёжного провайдера
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    trial_until: Mapped[date | None] = mapped_column(Date)
