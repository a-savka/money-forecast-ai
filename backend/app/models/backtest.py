from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import TimestampMixin


class BacktestRun(TimestampMixin, Base):
    """Прогон бэктеста одной стратегии на одном наборе данных — для экрана «Эксперименты»."""

    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    strategy: Mapped[str] = mapped_column(String(32))
    dataset: Mapped[str] = mapped_column(String(32))  # demo | me
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    cases: Mapped[list[Any]] = mapped_column(JSON, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    llm_cost: Mapped[float] = mapped_column(Float, default=0.0)
