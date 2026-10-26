from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(8))  # expense | income | transfer
    icon: Mapped[str] = mapped_column(String(32), default="circle")
    color: Mapped[str] = mapped_column(String(9), default="#94a3b8")
    # Необязательные траты — кандидаты на сокращение в рекомендациях
    is_discretionary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))


class CategoryRule(Base):
    """Правило категоризации. user_id=None — системное правило."""

    __tablename__ = "category_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    pattern: Mapped[str | None] = mapped_column(String(255))  # подстрока в описании (lower)
    mcc: Mapped[str | None] = mapped_column(String(4))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    priority: Mapped[int] = mapped_column(Integer, default=100)
