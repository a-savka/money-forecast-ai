from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import TimestampMixin


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    bank_name: Mapped[str | None] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16), default="card")  # card | cash | deposit
    source: Mapped[str] = mapped_column(String(16), default="manual")  # manual | csv | bank_mock
    balance_initial: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
