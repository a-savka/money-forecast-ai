"""Рекомендации по прогнозу: правила (работают всегда) + переформулировка LLM."""

from __future__ import annotations

import json

import pandas as pd
from pydantic import BaseModel

from app.forecasting.base import History
from app.forecasting.features import detect_recurring
from app.forecasting.schemas import ForecastResult
from app.llm import LLMError, get_provider, structured_call
from app.llm.prompts import load_prompt
from app.llm.schemas import RecommendationsRewrite
from app.services.categories import SYSTEM_CATEGORIES

NAMES = {c.slug: c.name for c in SYSTEM_CATEGORIES}
DISCRETIONARY = [c.slug for c in SYSTEM_CATEGORIES if c.is_discretionary]
MAX_CUT_SHARE = 0.3


class Recommendation(BaseModel):
    id: str
    type: str  # cash_gap | category_growth | save | subscriptions
    title: str
    text: str
    amount_effect: float  # ₽: сколько сэкономит / можно отложить
    category: str | None = None
    priority: int  # 1 — самое важное
    source: str = "rule"  # rule | llm


def _fmt(x: float) -> str:
    return f"{round(x / 100) * 100:,.0f} ₽".replace(",", " ")


def rule_recommendations(forecast: ForecastResult, history: History) -> list[Recommendation]:
    recs: list[Recommendation] = []
    by_cat = {c.category: c.expected - c.recurring for c in forecast.by_category}

    # 1. Риск кассового разрыва: какие необязательные траты сократить
    gap = forecast.cash_gap
    if gap.risk in ("medium", "high") and gap.min_balance_p10 < 0:
        # Сколько не хватает: по медианному сценарию, а если он в плюсе — по неудачному (P10)
        median_min = min(p.p50 for p in forecast.daily_balance)
        need = -median_min if median_min < 0 else -gap.min_balance_p10
        when = f" до {gap.first_negative_date.strftime('%d.%m')}" if gap.first_negative_date else ""
        shortfall = need
        for slug in sorted(DISCRETIONARY, key=lambda s: -by_cat.get(s, 0)):
            if need <= 0 or sum(r.type == "cash_gap" for r in recs) >= 3:
                break
            cut = min(by_cat.get(slug, 0) * MAX_CUT_SHARE, need)
            if cut < 300:
                continue
            need -= cut
            recs.append(
                Recommendation(
                    id=f"gap-{slug}",
                    type="cash_gap",
                    title=f"Сократите «{NAMES[slug]}» на {_fmt(cut)}",
                    text=(
                        f"Чтобы не уйти в минус{when}, уменьшите траты на «{NAMES[slug]}» "
                        f"примерно на {_fmt(cut)} — это около {round(MAX_CUT_SHARE * 100)}% "
                        "от ожидаемого."
                    ),
                    amount_effect=round(cut),
                    category=slug,
                    priority=1,
                )
            )

        # Сокращений не хватает (например, впереди крупный платёж) — нужен запас денег
        if need > 0:
            big = next(
                (u for u in forecast.upcoming if u.amount < 0 and -u.amount >= shortfall * 0.5),
                None,
            )
            reason = f" перед платежом «{big.name}» {big.date.strftime('%d.%m')}" if big else ""
            recs.insert(
                0,
                Recommendation(
                    id="gap-topup",
                    type="cash_gap",
                    title=f"Не хватает ≈ {_fmt(need)}{when}",
                    text=(
                        f"Одним сокращением трат разрыв не закрыть{reason}. Пополните счёт на "
                        f"{_fmt(need)} — например, из накоплений — "
                        "или договоритесь о переносе платежа."
                    ),
                    amount_effect=round(need),
                    priority=0,
                ),
            )

    # 2. Категории, где траты растут быстрее обычного
    txs = history.txs
    exp = txs[(txs["amount"] < 0) & (txs["kind"] == "expense")]
    as_of = pd.Timestamp(history.as_of)
    last30 = exp[exp["date"] > as_of - pd.Timedelta(days=30)].groupby("category")["amount"].sum()
    prev = exp[
        (exp["date"] <= as_of - pd.Timedelta(days=30))
        & (exp["date"] > as_of - pd.Timedelta(days=120))
    ]
    prev_avg = prev.groupby("category")["amount"].sum() / 3
    for slug in DISCRETIONARY:
        now, before = -float(last30.get(slug, 0)), -float(prev_avg.get(slug, 0))
        if before > 1000 and now > before * 1.25 and not any(r.category == slug for r in recs):
            growth = now / before - 1
            recs.append(
                Recommendation(
                    id=f"growth-{slug}",
                    type="category_growth",
                    title=f"«{NAMES[slug]}»: +{round(growth * 100)}% к обычному",
                    text=(
                        f"За последние 30 дней на «{NAMES[slug]}» ушло {_fmt(now)} при обычных "
                        f"{_fmt(before)} в месяц. Вернувшись к прежнему уровню, сэкономите "
                        f"{_fmt(now - before)}."
                    ),
                    amount_effect=round(now - before),
                    category=slug,
                    priority=2,
                )
            )

    # 3. Сколько можно отложить, если риск низкий
    if gap.risk == "low" and gap.min_balance_p10 > 3000:
        save = gap.min_balance_p10 * 0.6
        recs.append(
            Recommendation(
                id="save",
                type="save",
                title=f"Можно отложить {_fmt(save)}",
                text=(
                    "Даже в неудачном сценарии баланс не опустится ниже "
                    f"{_fmt(gap.min_balance_p10)}. "
                    f"Переведите {_fmt(save)} на накопительный счёт — запас останется."
                ),
                amount_effect=round(save),
                priority=3,
            )
        )

    # 4. Подписки
    recurring, _ = detect_recurring(txs, history.as_of)
    subs = [r for r in recurring if r.category == "subscriptions" and r.amount < 0]
    if subs:
        total = -sum(r.amount for r in subs)
        names = ", ".join(r.name for r in subs[:4])
        recs.append(
            Recommendation(
                id="subscriptions",
                type="subscriptions",
                title=f"Подписки: {_fmt(total)} в месяц",
                text=f"Активные подписки: {names}. Проверьте, всеми ли вы пользуетесь.",
                amount_effect=round(total),
                category="subscriptions",
                priority=4,
            )
        )
    return sorted(recs, key=lambda r: (r.priority, -r.amount_effect))


def llm_recommendations(
    recs: list[Recommendation], forecast: ForecastResult, provider_name: str | None = None
) -> tuple[list[Recommendation], dict]:
    """LLM переформулирует и приоритизирует рекомендации. Цифры остаются из правил."""
    if not recs:
        return recs, {}
    payload = {
        "risk": forecast.cash_gap.risk,
        "expected_expense": round(forecast.expected_expense),
        "period_end": forecast.period_end.isoformat(),
        "recommendations": [
            {"id": r.id, "title": r.title, "text": r.text, "amount_effect": r.amount_effect}
            for r in recs
        ],
    }
    try:
        res = structured_call(
            get_provider(provider_name),
            load_prompt("recommendations_v1"),
            "Рекомендации (JSON):\n" + json.dumps(payload, ensure_ascii=False),
            RecommendationsRewrite,
        )
    except LLMError as exc:
        return recs, {"llm_fallback": True, "llm_error": str(exc)[:200]}
    by_id = {r.id: r for r in recs}
    out: list[Recommendation] = []
    for priority, item in enumerate(res.data.items, start=1):
        base = by_id.pop(item.id, None)
        if base is None:
            continue
        out.append(
            base.model_copy(
                update={
                    "title": item.title,
                    "text": item.text,
                    "priority": priority,
                    "source": "llm",
                }
            )
        )
    out.extend(by_id.values())  # то, что LLM пропустила, не теряем
    return out, {"llm_provider": res.provider, "llm_tokens_in": res.usage.input_tokens}
