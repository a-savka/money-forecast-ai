from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import TimestampMixin


class AppEvent(TimestampMixin, Base):
    """События продуктовой аналитики (задел для пилота: time-to-value, конверсия в триал)."""

    __tablename__ = "app_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64), index=True)
    props: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
