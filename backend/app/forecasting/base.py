"""Общие типы прогнозного движка.

Каждая стратегия (H0–H3) получает одинаковую историю операций и возвращает
`StrategyOutput` — ожидаемые и сэмплированные переменные траты по дням.
Регулярные платежи, баланс и риск кассового разрыва считаются общим кодом
(`engine.py`), поэтому стратегии сравнимы между собой.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

import numpy as np
import pandas as pd

from app.forecasting.features import RecurringItem


@dataclass
class History:
    """Известные операции пользователя до даты `as_of` включительно.

    `txs` — DataFrame с колонками: date (datetime64), amount (float, расход < 0),
    category (slug), kind (expense/income/transfer), description.
    """

    txs: pd.DataFrame
    as_of: date
    balance: float

    @classmethod
    def from_records(cls, records: list[dict], as_of: date, balance: float) -> History:
        df = pd.DataFrame.from_records(
            records, columns=["date", "amount", "category", "kind", "description"]
        )
        df["date"] = pd.to_datetime(df["date"])
        df["amount"] = df["amount"].astype(float)
        df = df[df["date"] <= pd.Timestamp(as_of)].sort_values("date").reset_index(drop=True)
        return cls(df, as_of, balance)

    @property
    def start(self) -> date:
        return self.txs["date"].min().date() if len(self.txs) else self.as_of

    @property
    def days_of_history(self) -> int:
        return (self.as_of - self.start).days + 1


@dataclass
class ForecastContext:
    history: History
    horizon_end: date
    recurring: list[RecurringItem]
    # Индексы операций истории, признанных регулярными (исключаются из «переменных» трат)
    recurring_tx_index: set[int]
    # Ожидаемые даты поступления дохода в горизонте (для эффекта «после зарплаты»)
    income_dates: list[date]
    rng: np.random.Generator
    n_samples: int = 500

    @property
    def days(self) -> list[date]:
        start = self.history.as_of + timedelta(days=1)
        n = (self.horizon_end - self.history.as_of).days
        return [start + timedelta(days=i) for i in range(n)]

    def variable_expenses(self) -> pd.DataFrame:
        """Переменные траты истории: расходы без регулярных платежей и переводов."""
        df = self.history.txs
        mask = (
            (df["amount"] < 0) & (df["kind"] == "expense") & ~df.index.isin(self.recurring_tx_index)
        )
        out = df[mask].copy()
        out["spend"] = -out["amount"]
        return out


@dataclass
class StrategyOutput:
    """Переменные траты (положительные числа) на каждый день горизонта."""

    daily_mean: np.ndarray  # shape (days,)
    samples: np.ndarray  # shape (n_samples, days)
    by_category: dict[str, float]  # ожидаемые переменные траты за горизонт
    # Включает ли стратегия регулярные платежи и доходы сама (наивный H0)
    includes_recurring: bool = False
    expected_income_daily: np.ndarray | None = None
    # Нерегулярные поступления (фриланс, подработки): ожидание и сценарии по дням
    extra_income_mean: np.ndarray | None = None
    extra_income_samples: np.ndarray | None = None  # shape (n_samples, days)
    explanation: str = ""
    meta: dict = field(default_factory=dict)


class ForecastStrategy(Protocol):
    name: str
    title: str
    description: str

    def predict(self, ctx: ForecastContext) -> StrategyOutput: ...
