from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import TimestampMixin


class ImportJob(TimestampMixin, Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(16))  # csv | bank_mock | receipt
    # pending | preview | done | failed
    status: Mapped[str] = mapped_column(String(16), default="pending")
    file_name: Mapped[str | None] = mapped_column(String(255))
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_imported: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[Any]] = mapped_column(JSON, default=list)
    # Распарсенные строки до подтверждения пользователем
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
