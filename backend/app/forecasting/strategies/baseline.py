"""H0 — наивный прогноз «как в последние 30 дней».

Так работает обычная аналитика: средний дневной расход × оставшиеся дни.
Регулярные платежи и даты зарплаты не учитываются — это нижняя планка для сравнения.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from app.forecasting.base import ForecastContext, StrategyOutput

WINDOW_DAYS = 30


class BaselineStrategy:
    name = "baseline"
    title = "H0 · Среднее за 30 дней"
    description = "Средний дневной расход за последний месяц × оставшиеся дни."

    def predict(self, ctx: ForecastContext) -> StrategyOutput:
        h = ctx.history
        start = h.as_of - timedelta(days=WINDOW_DAYS - 1)
        df = h.txs[(h.txs["date"] >= pd.Timestamp(start)) & (h.txs["kind"] != "transfer")]
        idx = pd.date_range(start, h.as_of, freq="D")
        expense = (-df[df["amount"] < 0].groupby("date")["amount"].sum()).reindex(
            idx, fill_value=0.0
        )
        income = df[df["amount"] > 0].groupby("date")["amount"].sum().reindex(idx, fill_value=0.0)

        n_days = len(ctx.days)
        mean = float(expense.mean())
        samples = ctx.rng.choice(expense.to_numpy(), size=(ctx.n_samples, n_days), replace=True)

        by_cat = (-df[df["amount"] < 0].groupby("category")["amount"].sum()).to_dict()
        total = sum(by_cat.values()) or 1.0
        by_category = {c: v / total * mean * n_days for c, v in by_cat.items()}

        return StrategyOutput(
            daily_mean=np.full(n_days, mean),
            samples=samples,
            by_category=by_category,
            includes_recurring=True,
            expected_income_daily=np.full(n_days, float(income.mean())),
            explanation=(
                f"За последние {WINDOW_DAYS} дней вы тратили в среднем {mean:,.0f} ₽ в день. "
                "Если так продолжится, до конца периода уйдёт "
                f"{mean * n_days:,.0f} ₽.".replace(",", " ")
            ),
        )
