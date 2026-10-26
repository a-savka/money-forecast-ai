"""H1 — статистический прогноз.

1. Регулярные платежи и доходы — по расписанию (общий код движка).
2. Переменные траты — по категориям: средние по дням недели с экспоненциальным
   затуханием (свежие недели важнее старых).
3. Эффект «после зарплаты»: в первые дни после поступления дохода люди тратят больше.
4. Сезонность: если есть история за прошлый год, учитываем отличие этого месяца от среднего.
5. Неопределённость — бутстрэп реальных дневных трат того же дня недели.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.forecasting.base import ForecastContext, StrategyOutput

WINDOW_DAYS = 120
HALF_LIFE_DAYS = 45
PAYDAY_WINDOW = 5


def _weights(dates: pd.DatetimeIndex, as_of: date) -> np.ndarray:
    age = (pd.Timestamp(as_of) - dates).days.to_numpy()
    return 0.5 ** (age / HALF_LIFE_DAYS)


def _after_payday(days: pd.DatetimeIndex, paydays: list[date]) -> np.ndarray:
    pay = np.array([np.datetime64(p) for p in paydays], dtype="datetime64[D]")
    if pay.size == 0:
        return np.zeros(len(days), dtype=bool)
    d = days.to_numpy().astype("datetime64[D]")
    diff = (d[:, None] - pay[None, :]).astype(int)
    return ((diff >= 0) & (diff < PAYDAY_WINDOW)).any(axis=1)


class StatisticalStrategy:
    name = "statistical"
    title = "H1 · Статистика"
    description = (
        "Регулярные платежи по расписанию + переменные траты по дням недели "
        "с учётом свежести данных, эффекта зарплаты и сезонности."
    )

    def predict(self, ctx: ForecastContext) -> StrategyOutput:
        h = ctx.history
        var_full = ctx.variable_expenses()
        start = max(h.start, h.as_of - timedelta(days=WINDOW_DAYS - 1))
        idx = pd.date_range(start, h.as_of, freq="D")
        var = var_full[var_full["date"] >= pd.Timestamp(start)]

        # Матрица «день × категория» переменных трат
        table = (
            var.pivot_table(index="date", columns="category", values="spend", aggfunc="sum")
            .reindex(idx, fill_value=0.0)
            .fillna(0.0)
        )
        if table.shape[1] == 0:
            table = pd.DataFrame({"other": np.zeros(len(idx))}, index=idx)
        weights = _weights(idx, h.as_of)
        weekday = idx.day_of_week.to_numpy()

        # Эффект зарплаты по истории
        hist_paydays = [
            d.date()
            for d, a, i in zip(h.txs["date"], h.txs["amount"], h.txs.index, strict=True)
            if a > 0 and i in ctx.recurring_tx_index
        ]
        hist_after = _after_payday(idx, hist_paydays)
        totals = table.sum(axis=1).to_numpy()
        overall = np.average(totals, weights=weights) if totals.any() else 0.0
        f_pay = f_norm = 1.0
        if overall > 0 and hist_after.any() and (~hist_after).any():
            f_pay = float(
                np.clip(
                    np.average(totals[hist_after], weights=weights[hist_after]) / overall, 0.7, 2.0
                )
            )
            f_norm = float(
                np.clip(
                    np.average(totals[~hist_after], weights=weights[~hist_after]) / overall,
                    0.5,
                    1.3,
                )
            )

        # Средние по дням недели для каждой категории (если истории мало — общее среднее)
        enough = len(idx) >= 28
        wd_means = np.zeros((7, table.shape[1]))
        for wd in range(7):
            mask = weekday == wd if enough else np.ones(len(idx), dtype=bool)
            if mask.any():
                wd_means[wd] = np.average(table.to_numpy()[mask], axis=0, weights=weights[mask])

        days = pd.DatetimeIndex(ctx.days)
        future_after = _after_payday(days, ctx.income_dates)
        factor = np.where(future_after, f_pay, f_norm)
        season = self._seasonality(var_full, h, days)
        per_cat = wd_means[days.day_of_week.to_numpy()] * (factor * season)[:, None]  # (days, cats)
        daily_mean = per_cat.sum(axis=1)

        # Бутстрэп: реальные дневные суммы того же дня недели, масштабированные к ожидаемому
        samples = np.zeros((ctx.n_samples, len(days)))
        probs = weights / weights.sum()
        for j, d in enumerate(days):
            mask = weekday == d.weekday() if enough else np.ones(len(idx), dtype=bool)
            pool, p = totals[mask], probs[mask] / probs[mask].sum()
            base = float(np.dot(pool, p)) or 1.0
            samples[:, j] = ctx.rng.choice(pool, size=ctx.n_samples, p=p) * daily_mean[j] / base

        by_category = {c: float(v) for c, v in zip(table.columns, per_cat.sum(axis=0), strict=True)}
        recurring_out = sum(-r.amount for r in ctx.recurring if r.amount < 0)
        return StrategyOutput(
            daily_mean=daily_mean,
            samples=samples,
            by_category=by_category,
            explanation=self._explain(daily_mean, f_pay, recurring_out, ctx),
            meta={"payday_factor": round(f_pay, 2), "season": round(float(season.mean()), 2)},
        )

    @staticmethod
    def _seasonality(var_full: pd.DataFrame, h, days: pd.DatetimeIndex) -> np.ndarray:
        """Отношение переменных трат в том же месяце год назад к среднему месяцу за год."""
        if h.days_of_history < 330:
            return np.ones(len(days))
        year = var_full[var_full["date"] > pd.Timestamp(h.as_of - timedelta(days=365))]
        monthly = year.groupby(year["date"].dt.month)["spend"].sum()
        if len(monthly) < 10:
            return np.ones(len(days))
        avg = monthly.mean()
        factors = {m: float(np.clip(v / avg, 0.85, 1.3)) for m, v in monthly.items()}
        return np.array([factors.get(d.month, 1.0) for d in days])

    @staticmethod
    def _explain(
        daily_mean: np.ndarray, f_pay: float, recurring_out: float, ctx: ForecastContext
    ) -> str:
        parts = [f"Переменные траты — около {daily_mean.mean():,.0f} ₽ в день".replace(",", " ")]
        n_rec = sum(1 for r in ctx.recurring if r.amount < 0)
        if n_rec:
            parts.append(f"учтено {n_rec} регулярных платежей")
        if f_pay > 1.1:
            parts.append(
                f"после зарплаты вы тратите примерно на {round((f_pay - 1) * 100)}% больше обычного"
            )
        return "; ".join(parts) + "."
