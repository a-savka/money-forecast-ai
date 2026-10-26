import datetime as dt

from pydantic import BaseModel


class CategoryForecast(BaseModel):
    category: str  # slug
    expected: float  # ожидаемые траты за горизонт (включая регулярные)
    recurring: float  # из них регулярные платежи


class BalancePoint(BaseModel):
    date: dt.date
    expected: float
    p10: float
    p50: float
    p90: float


class UpcomingPayment(BaseModel):
    date: dt.date
    name: str
    category: str
    amount: float  # со знаком: доход > 0
    confidence: float


class CashGap(BaseModel):
    risk: str  # low | medium | high
    probability: float
    first_negative_date: dt.date | None
    min_balance_p10: float


class ForecastResult(BaseModel):
    strategy: str
    as_of: dt.date
    period_end: dt.date
    current_balance: float
    expected_expense: float
    expected_expense_p10: float
    expected_expense_p90: float
    expected_income: float
    expected_balance_end: float
    by_category: list[CategoryForecast]
    daily_balance: list[BalancePoint]
    upcoming: list[UpcomingPayment]
    cash_gap: CashGap
    safe_to_spend_per_day: float
    explanation: str = ""
