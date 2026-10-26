"""H2 — статистика + LLM.

H1 считает числа. В LLM уходит только агрегированная сводка (суммы по категориям,
тренды, праздники, даты зарплаты) — без описаний операций, номеров карт и имён.
LLM возвращает поправочные коэффициенты по категориям (ограничены ±30%) и объяснение.
При любой ошибке LLM результат совпадает с H1 (fallback).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.forecasting.base import ForecastContext, StrategyOutput
from app.forecasting.strategies.statistical import StatisticalStrategy
from app.llm import LLMError, get_provider, structured_call
from app.llm.prompts import load_prompt
from app.llm.schemas import ForecastAdjustment
from app.services.categories import SYSTEM_CATEGORIES

PROMPT = "forecast_adjust_v1"
MAX_ADJUSTMENT = 0.3
CATEGORY_NAMES = {c.slug: c.name for c in SYSTEM_CATEGORIES}

# Нерабочие праздничные дни РФ (без переносов)
HOLIDAYS = {
    (1, 1): "Новый год",
    (1, 7): "Рождество",
    (2, 23): "23 февраля",
    (3, 8): "8 марта",
    (5, 1): "1 мая",
    (5, 9): "9 мая",
    (6, 12): "День России",
    (11, 4): "День народного единства",
    (12, 31): "31 декабря",
}


class StatLLMStrategy:
    name = "stat_llm"
    title = "H2 · Статистика + LLM"
    description = (
        "Статистический прогноз H1, скорректированный языковой моделью с учётом трендов, "
        "праздников и сезонности. LLM видит только агрегаты."
    )

    def __init__(self, provider_name: str | None = None):
        self.provider_name = provider_name
        self.base = StatisticalStrategy()

    def predict(self, ctx: ForecastContext) -> StrategyOutput:
        out = self.base.predict(ctx)
        per_cat: np.ndarray = out.meta["per_category_daily"]
        categories: list[str] = out.meta["categories"]
        payload = build_payload(ctx, categories, per_cat)

        try:
            provider = get_provider(self.provider_name)
            res = structured_call(
                provider,
                load_prompt(PROMPT),
                "Данные пользователя (JSON):\n" + json.dumps(payload, ensure_ascii=False),
                ForecastAdjustment,
            )
        except LLMError as exc:
            out.meta.update({"llm_fallback": True, "llm_error": str(exc)[:200]})
            out.explanation += " (LLM недоступна — показан статистический прогноз.)"
            return out

        factors = np.ones(len(categories))
        applied = []
        for adj in res.data.adjustments:
            if adj.category not in categories:
                continue
            f = float(np.clip(adj.factor, 1 - MAX_ADJUSTMENT, 1 + MAX_ADJUSTMENT))
            factors[categories.index(adj.category)] = f
            applied.append({"category": adj.category, "factor": round(f, 2), "reason": adj.reason})

        new_per_cat = per_cat * factors[None, :]
        new_daily = new_per_cat.sum(axis=1)
        scale = np.divide(
            new_daily, out.daily_mean, out=np.ones_like(new_daily), where=out.daily_mean > 0
        )

        out.daily_mean = new_daily
        out.samples = out.samples * scale[None, :]
        out.by_category = {
            c: float(v) for c, v in zip(categories, new_per_cat.sum(axis=0), strict=True)
        }
        out.explanation = res.data.summary + " " + out.explanation
        out.meta.update(
            {
                "llm_provider": res.provider,
                "llm_model": res.model,
                "llm_tokens_in": res.usage.input_tokens,
                "llm_tokens_out": res.usage.output_tokens,
                "llm_latency_ms": res.latency_ms,
                "llm_cached": res.cached,
                "llm_adjustments": applied,
                "prompt": PROMPT,
            }
        )
        return out


def build_payload(ctx: ForecastContext, categories: list[str], per_cat: np.ndarray) -> dict:
    """Агрегированная сводка для LLM. Никаких описаний операций и персональных данных."""
    h = ctx.history
    var = ctx.variable_expenses()
    as_of = pd.Timestamp(h.as_of)
    last_2w = var[var["date"] > as_of - pd.Timedelta(days=14)].groupby("category")["spend"].sum()
    prev_90 = var[
        (var["date"] <= as_of - pd.Timedelta(days=14))
        & (var["date"] > as_of - pd.Timedelta(days=104))
    ]
    avg_2w = prev_90.groupby("category")["spend"].sum() / (90 / 14)

    monthly = (
        var[var["date"] > as_of - pd.Timedelta(days=92)]
        .groupby([var["date"].dt.to_period("M").astype(str), "category"])["spend"]
        .sum()
        .round()
    )
    rows = []
    forecast = per_cat.sum(axis=0)
    for i, c in enumerate(categories):
        avg = float(avg_2w.get(c, 0))
        recent = float(last_2w.get(c, 0))
        rows.append(
            {
                "slug": c,
                "name": CATEGORY_NAMES.get(c, c),
                "forecast": round(float(forecast[i])),
                "last_2_weeks": round(recent),
                "avg_2_weeks": round(avg),
                "trend_2w_vs_avg": round(recent / avg, 2) if avg > 0 else 1.0,
                "by_month": {m: float(v) for (m, cat), v in monthly.items() if cat == c},
            }
        )
    days = ctx.days
    holidays = sorted({HOLIDAYS[(d.month, d.day)] for d in days if (d.month, d.day) in HOLIDAYS})
    return {
        "as_of": h.as_of.isoformat(),
        "horizon_end": ctx.horizon_end.isoformat(),
        "horizon_days": len(days),
        "horizon_month": ctx.horizon_end.month,
        "weekends_in_horizon": sum(d.weekday() >= 5 for d in days),
        "holidays_in_horizon": holidays,
        "income_dates": [d.isoformat() for d in ctx.income_dates],
        "categories": sorted(rows, key=lambda r: -r["forecast"]),
    }
