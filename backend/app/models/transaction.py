import datetime as dt
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin
from app.models.category import Category


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "dedup_hash", name="uq_transaction_dedup"),
        Index("ix_transactions_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    date: Mapped[dt.date] = mapped_column(Date)
    # Расход < 0, доход > 0
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    description: Mapped[str] = mapped_column(String(512), default="")
    merchant: Mapped[str | None] = mapped_column(String(255))
    mcc: Mapped[str | None] = mapped_column(String(4))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    # rule | bank | mcc | keyword | llm | user
    category_source: Mapped[str] = mapped_column(String(8), default="user")
    # manual | csv | bank_mock | receipt
    source: Mapped[str] = mapped_column(String(16), default="manual")
    external_id: Mapped[str | None] = mapped_column(String(128))
    dedup_hash: Mapped[str | None] = mapped_column(String(64))
    import_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="SET NULL")
    )
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)

    category: Mapped[Category | None] = relationship(lazy="joined")
