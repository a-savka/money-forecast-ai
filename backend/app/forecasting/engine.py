"""Сборка прогноза: стратегия + регулярные платежи → баланс, риск, safe-to-spend."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from app.forecasting.base import ForecastContext, ForecastStrategy, History
from app.forecasting.features import detect_recurring, schedule
from app.forecasting.schemas import (
    BalancePoint,
    CashGap,
    CategoryForecast,
    ForecastResult,
    UpcomingPayment,
)

# Пороги уровня риска по вероятности уйти в минус
RISK_LEVELS = [(0.35, "high"), (0.1, "medium"), (0.0, "low")]
# Подушка безопасности при расчёте «сколько можно тратить в день»
SAFETY_BUFFER = 0.05


def build_context(
    history: History, horizon_end: date, *, n_samples: int = 500, seed: int = 0
) -> ForecastContext:
    recurring, rec_idx = detect_recurring(history.txs, history.as_of)
    ctx = ForecastContext(
        history=history,
        horizon_end=horizon_end,
        recurring=recurring,
        recurring_tx_index=rec_idx,
        income_dates=[],
        rng=np.random.default_rng(seed),
        n_samples=n_samples,
    )
    _, income, _ = schedule([r for r in recurring if r.kind == "income"], ctx.days)
    ctx.income_dates = [d for d, v in zip(ctx.days, income, strict=True) if v > 0]
    return ctx


def run_forecast(
    strategy: ForecastStrategy,
    history: History,
    horizon_end: date,
    *,
    n_samples: int = 500,
    seed: int = 0,
) -> ForecastResult:
    ctx = build_context(history, horizon_end, n_samples=n_samples, seed=seed)
    days = ctx.days
    if not days:
        raise ValueError("Горизонт прогноза должен быть позже даты истории")
    out = strategy.predict(ctx)

    if out.includes_recurring:
        rec_expense = np.zeros(len(days))
        rec_income = out.expected_income_daily if out.expected_income_daily is not None else 0
        events = []
    else:
        rec_expense, rec_income, events = schedule(ctx.recurring, days)

    extra_mean = out.extra_income_mean if out.extra_income_mean is not None else np.zeros(len(days))
    extra_samples = out.extra_income_samples if out.extra_income_samples is not None else 0

    # Сценарии баланса: переменные траты сэмплирует стратегия, регулярные — по расписанию
    flows = rec_income + extra_samples - rec_expense - out.samples  # (n, days)
    paths = history.balance + np.cumsum(flows, axis=1)
    mean_path = history.balance + np.cumsum(rec_income + extra_mean - rec_expense - out.daily_mean)

    p10, p50, p90 = np.percentile(paths, [10, 50, 90], axis=0)
    total_expense_samples = out.samples.sum(axis=1) + rec_expense.sum()
    min_balance = paths.min(axis=1)
    probability = float((min_balance < 0).mean())
    level = next(name for threshold, name in RISK_LEVELS if probability >= threshold)

    first_negative = None
    if probability > 0:
        neg_days = [int(np.argmax(p < 0)) for p in paths if (p < 0).any()]
        first_negative = days[int(np.median(neg_days))]

    expected_income = float(np.sum(rec_income) + np.sum(extra_mean))
    expected_expense = float(out.daily_mean.sum() + rec_expense.sum())
    remaining_days = len(days)
    # Для «можно тратить в день» нерегулярный доход берём консервативно — наполовину
    spendable = history.balance + float(np.sum(rec_income)) + 0.5 * float(np.sum(extra_mean))
    spendable -= float(rec_expense.sum())
    spendable -= SAFETY_BUFFER * max(expected_income, history.balance, 0)
    safe_per_day = max(0.0, spendable / remaining_days)

    rec_by_category: dict[str, float] = {}
    for _, item in events:
        if item.amount < 0:
            rec_by_category[item.category] = rec_by_category.get(item.category, 0) - item.amount
    categories = sorted(
        set(out.by_category) | set(rec_by_category),
        key=lambda c: -(out.by_category.get(c, 0) + rec_by_category.get(c, 0)),
    )

    return ForecastResult(
        strategy=getattr(strategy, "name", "unknown"),
        as_of=history.as_of,
        period_end=horizon_end,
        current_balance=round(history.balance, 2),
        expected_expense=round(expected_expense, 2),
        expected_expense_p10=round(float(np.percentile(total_expense_samples, 10)), 2),
        expected_expense_p90=round(float(np.percentile(total_expense_samples, 90)), 2),
        expected_income=round(expected_income, 2),
        expected_balance_end=round(float(mean_path[-1]), 2),
        by_category=[
            CategoryForecast(
                category=c,
                expected=round(out.by_category.get(c, 0) + rec_by_category.get(c, 0), 2),
                recurring=round(rec_by_category.get(c, 0), 2),
            )
            for c in categories
        ],
        daily_balance=[
            BalancePoint(
                date=d,
                expected=round(float(mean_path[i]), 2),
                p10=round(float(p10[i]), 2),
                p50=round(float(p50[i]), 2),
                p90=round(float(p90[i]), 2),
            )
            for i, d in enumerate(days)
        ],
        upcoming=[
            UpcomingPayment(
                date=d,
                name=item.name,
                category=item.category,
                amount=round(item.amount, 2),
                confidence=item.confidence,
            )
            for d, item in events
        ],
        cash_gap=CashGap(
            risk=level,
            probability=round(probability, 3),
            first_negative_date=first_negative,
            min_balance_p10=round(float(np.percentile(min_balance, 10)), 2),
        ),
        safe_to_spend_per_day=round(safe_per_day, 2),
        explanation=out.explanation,
        model_info={
            k: v for k, v in out.meta.items() if not k.startswith("per_") and k != "categories"
        },
    )


def month_end(d: date) -> date:
    nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return nxt - timedelta(days=1)
