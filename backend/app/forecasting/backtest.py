"""Бэктест стратегий прогноза по протоколу rolling origin.

Для каждой точки отсечения стратегия видит только операции до неё и прогнозирует траты
до конца месяца; прогноз сравнивается с фактом. Метрики — MAE, WAPE, MAPE, смещение,
покрытие интервала P10–P90, ошибка по категориям, precision/recall кассового разрыва,
время ответа и расход токенов LLM.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.forecasting.base import ForecastStrategy, History
from app.forecasting.engine import month_end, run_forecast

DEFAULT_CUTOFF_DAYS = (1, 10, 20)
# Оценка стоимости LLM: ≈ 0,2 ₽ за 1000 токенов (порядок цен GigaChat Lite / YandexGPT Lite)
LLM_RUB_PER_1K_TOKENS = 0.2
# Прогноз «риск разрыва» засчитываем как предупреждение, начиная с этого уровня
WARNING_LEVELS = ("medium", "high")


@dataclass
class Dataset:
    """Полная история одного пользователя (синтетика или реальная выписка)."""

    name: str
    history: History  # as_of — последний день данных, balance — баланс на этот день

    def cut(self, cutoff: date) -> History:
        txs = self.history.txs
        after = txs[txs["date"] > pd.Timestamp(cutoff)]
        balance = self.history.balance - float(after["amount"].sum())
        return History(txs[txs["date"] <= pd.Timestamp(cutoff)].copy(), cutoff, balance)


@dataclass
class CaseResult:
    dataset: str
    cutoff: date
    period_end: date
    actual: float
    forecast: float
    p10: float
    p90: float
    actual_gap: bool
    predicted_risk: str
    category_abs_error: float
    latency_ms: float
    llm_tokens: int

    @property
    def error(self) -> float:
        return self.forecast - self.actual


def cutoffs_for(
    ds: Dataset, months: int = 6, days: tuple[int, ...] = DEFAULT_CUTOFF_DAYS
) -> list[date]:
    """Точки отсечения: заданные числа месяцев за последние `months` месяцев.

    Отсечение берётся, только если до него ≥ 90 дней истории, а конец месяца есть в данных.
    """
    last = ds.history.as_of
    min_cutoff = ds.history.start + timedelta(days=90)
    out = []
    y, m = last.year, last.month
    for _ in range(months + 1):
        for d in days:
            c = date(y, m, d)
            if min_cutoff <= c and month_end(c) <= last and c < month_end(c):
                out.append(c)
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return sorted(out)[-months * len(days) :]


def _actual(ds: Dataset, cutoff: date, end: date) -> tuple[float, dict[str, float], bool]:
    """Факт: траты за период, траты по категориям и был ли уход в минус."""
    txs = ds.history.txs
    window = txs[
        (txs["date"] > pd.Timestamp(cutoff))
        & (txs["date"] <= pd.Timestamp(end))
        & (txs["kind"] != "transfer")
    ]
    spend = window[window["amount"] < 0]
    by_cat = (-spend.groupby("category")["amount"].sum()).to_dict()
    # Баланс по дням без переводов между своими счетами — так же считает прогноз
    start_balance = ds.cut(cutoff).balance
    daily = window.groupby("date")["amount"].sum().sort_index()
    min_balance = start_balance + float(daily.cumsum().min()) if len(daily) else start_balance
    return float(-spend["amount"].sum()), by_cat, min_balance < 0


def run_case(strategy: ForecastStrategy, ds: Dataset, cutoff: date, *, seed: int = 0) -> CaseResult:
    end = month_end(cutoff)
    history = ds.cut(cutoff)
    started = time.perf_counter()
    f = run_forecast(strategy, history, end, n_samples=300, seed=seed)
    latency = (time.perf_counter() - started) * 1000

    actual, actual_by_cat, actual_gap = _actual(ds, cutoff, end)
    forecast_by_cat = {c.category: c.expected for c in f.by_category}
    cats = set(actual_by_cat) | set(forecast_by_cat)
    cat_error = sum(abs(forecast_by_cat.get(c, 0) - actual_by_cat.get(c, 0)) for c in cats)
    info = f.model_info
    return CaseResult(
        dataset=ds.name,
        cutoff=cutoff,
        period_end=end,
        actual=round(actual, 2),
        forecast=f.expected_expense,
        p10=f.expected_expense_p10,
        p90=f.expected_expense_p90,
        actual_gap=actual_gap,
        predicted_risk=f.cash_gap.risk,
        category_abs_error=round(cat_error, 2),
        latency_ms=round(latency, 1),
        llm_tokens=int(info.get("llm_tokens_in", 0)) + int(info.get("llm_tokens_out", 0)),
    )


def metrics(cases: list[CaseResult]) -> dict[str, float | int | None]:
    if not cases:
        return {"cases": 0}
    actual = np.array([c.actual for c in cases])
    forecast = np.array([c.forecast for c in cases])
    err = forecast - actual
    nonzero = actual > 0
    covered = [c.p10 <= c.actual <= c.p90 for c in cases]
    warned = np.array([c.predicted_risk in WARNING_LEVELS for c in cases])
    gaps = np.array([c.actual_gap for c in cases])
    tp = int((warned & gaps).sum())
    tokens = sum(c.llm_tokens for c in cases)
    return {
        "cases": len(cases),
        "mae": round(float(np.abs(err).mean()), 0),
        "wape": round(float(np.abs(err).sum() / max(actual.sum(), 1)), 4),
        "mape": round(float((np.abs(err[nonzero]) / actual[nonzero]).mean()), 4)
        if nonzero.any()
        else None,
        "bias": round(float(err.sum() / max(actual.sum(), 1)), 4),
        "coverage_p10_p90": round(float(np.mean(covered)), 3),
        "category_wape": round(
            float(sum(c.category_abs_error for c in cases) / max(actual.sum(), 1)), 4
        ),
        "gap_cases": int(gaps.sum()),
        "gap_precision": round(tp / int(warned.sum()), 3) if warned.any() else None,
        "gap_recall": round(tp / int(gaps.sum()), 3) if gaps.any() else None,
        "latency_ms": round(float(np.mean([c.latency_ms for c in cases])), 1),
        "llm_tokens": tokens,
        "llm_cost_rub": round(tokens / 1000 * LLM_RUB_PER_1K_TOKENS, 2),
    }


@dataclass
class StrategyReport:
    strategy: str
    metrics: dict
    cases: list[CaseResult]
    duration_ms: int

    def cases_json(self) -> list[dict]:
        return [
            {**asdict(c), "cutoff": c.cutoff.isoformat(), "period_end": c.period_end.isoformat()}
            for c in self.cases
        ]


def run_backtest(
    strategies: dict[str, ForecastStrategy],
    datasets: list[Dataset],
    *,
    months: int = 6,
    cutoff_days: tuple[int, ...] = DEFAULT_CUTOFF_DAYS,
) -> list[StrategyReport]:
    plan = [(ds, c) for ds in datasets for c in cutoffs_for(ds, months, cutoff_days)]
    reports = []
    for name, strategy in strategies.items():
        started = time.perf_counter()
        cases = [run_case(strategy, ds, c) for ds, c in plan]
        reports.append(
            StrategyReport(
                strategy=name,
                metrics=metrics(cases),
                cases=cases,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )
    return reports
