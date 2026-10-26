"""Подготовка данных для прогноза: дневные ряды и детекция регулярных платежей."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

# Периоды регулярности: (название, длина в днях, допустимый диапазон медианного интервала)
PERIODS = [("monthly", 30, (25, 36)), ("biweekly", 14, (12, 17)), ("weekly", 7, (6, 8))]


@dataclass
class RecurringItem:
    key: str
    name: str
    category: str
    kind: str  # expense | income
    amount: float  # со знаком
    period: str
    period_days: int
    day_of_month: int | None
    last_date: date
    occurrences: int
    confidence: float

    def upcoming(self, after: date, until: date) -> list[date]:
        """Ожидаемые даты в интервале (after, until]."""
        out: list[date] = []
        if self.period == "monthly":
            assert self.day_of_month is not None
            y, m = self.last_date.year, self.last_date.month
            for _ in range(24):
                y, m = (y + 1, 1) if m == 12 else (y, m + 1)
                d = date(y, m, min(self.day_of_month, calendar.monthrange(y, m)[1]))
                if d > until:
                    break
                if d > after:
                    out.append(d)
                elif (after - d).days <= 5 and d > self.last_date + timedelta(days=20):
                    # Платёж этого месяца немного запаздывает — ждём его в ближайшие дни
                    out.append(after + timedelta(days=1))
        else:
            d = self.last_date + timedelta(days=self.period_days)
            while d <= until:
                if d > after:
                    out.append(d)
                d += timedelta(days=self.period_days)
        return out


def description_key(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[«»\"'№]", " ", text)
    text = re.sub(r"\d+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_recurring(
    txs: pd.DataFrame, as_of: date, lookback_days: int = 200
) -> tuple[list[RecurringItem], set[int]]:
    """Находит регулярные платежи и доходы.

    Признаки: одно и то же описание ≥ 3 раз, стабильный интервал (неделя/2 недели/месяц),
    стабильная сумма. Возвращает список регулярных статей и индексы их операций в `txs`.
    """
    df = txs[
        (txs["kind"] != "transfer") & (txs["date"] > pd.Timestamp(as_of - timedelta(lookback_days)))
    ]
    if df.empty:
        return [], set()
    df = df.assign(key=df["description"].map(description_key), sign=np.sign(df["amount"]))

    items: list[RecurringItem] = []
    indices: set[int] = set()
    for (key, sign), g in df.groupby(["key", "sign"]):
        if len(g) < 3 or not key:
            continue
        dates = g["date"].sort_values()
        intervals = dates.diff().dt.days.dropna()
        median_interval = float(intervals.median())
        period = next((p for p in PERIODS if p[2][0] <= median_interval <= p[2][1]), None)
        if period is None:
            continue
        name, days, _ = period
        # Регулярные траты по описанию (например, «ПЯТЁРОЧКА») бывают и чаще —
        # требуем стабильный интервал и стабильную сумму
        interval_cv = float(intervals.std(ddof=0) / median_interval) if len(intervals) > 1 else 0.0
        amounts = g["amount"].abs()
        amount_cv = float(amounts.std(ddof=0) / amounts.mean())
        if interval_cv > 0.35 or amount_cv > 0.35:
            continue
        if name == "monthly" and dates.dt.to_period("M").nunique() < 3:
            continue
        last = dates.iloc[-1].date()
        if (as_of - last).days > days + 10:
            continue  # платёж прекратился
        confidence = max(0.0, 1 - interval_cv - amount_cv) * min(1.0, len(g) / 6)
        recent = g.sort_values("date").tail(3)
        items.append(
            RecurringItem(
                key=str(key),
                name=str(g["description"].iloc[-1]),
                category=str(g["category"].mode().iloc[0]),
                kind="income" if sign > 0 else "expense",
                amount=float(recent["amount"].median()),
                period=name,
                period_days=days,
                day_of_month=int(np.median(dates.dt.day)) if name == "monthly" else None,
                last_date=last,
                occurrences=len(g),
                confidence=round(confidence, 2),
            )
        )
    # Помечаем все вхождения найденных статей за всю историю, а не только за окно детекции
    if items:
        found = {(i.key, 1.0 if i.amount > 0 else -1.0) for i in items}
        full_keys = txs["description"].map(description_key)
        full_signs = np.sign(txs["amount"])
        for idx, key, sign in zip(txs.index, full_keys, full_signs, strict=True):
            if (key, sign) in found and txs.at[idx, "kind"] != "transfer":
                indices.add(int(idx))
    items.sort(key=lambda r: abs(r.amount), reverse=True)
    return items, indices


def schedule(items: list[RecurringItem], days: list[date]) -> tuple[np.ndarray, np.ndarray, list]:
    """Раскладывает регулярные статьи по дням горизонта.

    Возвращает (регулярные расходы по дням >0, доходы по дням >0, список событий).
    """
    if not days:
        return np.zeros(0), np.zeros(0), []
    index = {d: i for i, d in enumerate(days)}
    expense = np.zeros(len(days))
    income = np.zeros(len(days))
    events = []
    for item in items:
        for d in item.upcoming(days[0] - timedelta(days=1), days[-1]):
            i = index[d]
            if item.amount < 0:
                expense[i] += -item.amount
            else:
                income[i] += item.amount
            events.append((d, item))
    events.sort(key=lambda e: e[0])
    return expense, income, events


def daily_totals(variable: pd.DataFrame, start: date, end: date) -> pd.Series:
    """Сумма переменных трат по каждому дню (включая дни без трат)."""
    idx = pd.date_range(start, end, freq="D")
    if variable.empty:
        return pd.Series(0.0, index=idx)
    return variable.groupby("date")["spend"].sum().reindex(idx, fill_value=0.0)
