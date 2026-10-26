from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class BudgetIn(BaseModel):
    category_id: int
    limit: Decimal = Field(gt=0, le=10_000_000)


class BudgetOut(BaseModel):
    id: int
    category_id: int
    limit: float
    spent: float
    remaining: float
    projected: float
    daily_pace: float
    days_left_in_month: int
    exhausted_in_days: int | None
    status: Literal["ok", "warning", "over"]


class BudgetSuggestion(BaseModel):
    category_id: int
    limit: float
