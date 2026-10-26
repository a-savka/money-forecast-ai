import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class BacktestRequest(BaseModel):
    strategies: list[str] | None = None  # None — все стратегии
    dataset: Literal["demo", "me"] = "demo"
    months: int = Field(3, ge=1, le=12)


class BacktestCase(BaseModel):
    dataset: str
    cutoff: dt.date
    period_end: dt.date
    actual: float
    forecast: float
    p10: float
    p90: float
    actual_gap: bool
    predicted_risk: str
    latency_ms: float


class BacktestRunOut(ORMModel):
    id: int
    strategy: str
    dataset: str
    params: dict
    metrics: dict
    cases: list[BacktestCase]
    duration_ms: int
    llm_cost: float
    created_at: dt.datetime
