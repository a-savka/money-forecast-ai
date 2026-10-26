"""H3 — ML-прогноз: глобальная модель LightGBM.

1. Регулярные платежи, доходы и нерегулярные поступления — как в H1 (общий код движка).
2. Переменные траты по дням предсказывает градиентный бустинг. Модель одна на всех
   пользователей: обучается на синтетических «случайных» профилях (демо-профили
   в обучение не попадают), поэтому работает даже при короткой истории.
3. Чтобы модель переносилась между людьми с разным уровнем трат, цель нормирована:
   траты дня / средние траты за последние 28 дней. Признаки — календарь, дни до/после
   зарплаты, праздники, шаг горизонта и отношения уровней (7/90 дней к 28).
4. Неопределённость — квантильная регрессия (P10/P50/P90), сценарии сэмплируются
   из кусочно-линейной функции распределения.
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from app.config import get_settings
from app.forecasting.base import ForecastContext, History, StrategyOutput
from app.forecasting.features import description_key
from app.forecasting.strategies.stat_llm import HOLIDAYS
from app.forecasting.strategies.statistical import StatisticalStrategy

MODEL_FILE = "ml_gbm.json"
HORIZON_DAYS = 35
LEVEL_DAYS = 28
QUANTILES = (0.1, 0.5, 0.9)
FEATURES = [
    "step",
    "dow",
    "dom",
    "month",
    "is_weekend",
    "is_holiday",
    "days_since_pay",
    "days_to_pay",
    "dow_ratio",
    "lvl7_rel",
    "lvl90_rel",
]
FEATURE_TITLES = {
    "step": "дальность прогноза",
    "dow": "день недели",
    "dom": "день месяца",
    "month": "месяц",
    "is_weekend": "выходные",
    "is_holiday": "праздники",
    "days_since_pay": "дни после зарплаты",
    "days_to_pay": "дни до зарплаты",
    "dow_ratio": "ваши траты по дням недели",
    "lvl7_rel": "траты последней недели",
    "lvl90_rel": "траты за 3 месяца",
}
# Демо-профили обучаются на отдельных сидах, чтобы модель не «видела» тестовые данные
TRAIN_SEED_OFFSET = 10_000


def _level(series: pd.Series, as_of: date, days: int) -> float:
    start = pd.Timestamp(as_of - timedelta(days=days - 1))
    return float(series[series.index >= start].sum()) / days


def make_features(ctx: ForecastContext) -> tuple[pd.DataFrame, float]:
    """Признаки для каждого дня горизонта и уровень трат (среднее за 28 дней)."""
    h = ctx.history
    var = ctx.variable_expenses()
    idx = pd.date_range(max(h.start, h.as_of - timedelta(days=89)), h.as_of, freq="D")
    daily = var.groupby("date")["spend"].sum().reindex(idx, fill_value=0.0)

    lvl28 = _level(daily, h.as_of, LEVEL_DAYS)
    lvl7 = _level(daily, h.as_of, 7)
    lvl90 = float(daily.mean()) if len(daily) else 0.0
    base = lvl28 or lvl90 or 1.0

    # Насколько каждый день недели дороже среднего (за 90 дней)
    by_dow = daily.groupby(daily.index.day_of_week).mean()
    dow_ratio = {d: (float(by_dow.get(d, 0.0)) / lvl90 if lvl90 else 1.0) for d in range(7)}

    hist_pay = sorted(
        {
            d.date()
            for d, a, i in zip(h.txs["date"], h.txs["amount"], h.txs.index, strict=True)
            if a > 0 and i in ctx.recurring_tx_index
        }
    )
    paydays = np.array(hist_pay + list(ctx.income_dates), dtype="datetime64[D]")

    days = pd.DatetimeIndex(ctx.days)
    d64 = days.to_numpy().astype("datetime64[D]")
    if paydays.size:
        diff = (d64[:, None] - paydays[None, :]).astype(int)
        since = np.where(diff >= 0, diff, 999).min(axis=1)
        to = np.where(diff <= 0, -diff, 999).min(axis=1)
    else:
        since = to = np.full(len(days), 999)

    X = pd.DataFrame(
        {
            "step": np.arange(1, len(days) + 1),
            "dow": days.day_of_week,
            "dom": days.day,
            "month": days.month,
            "is_weekend": (days.day_of_week >= 5).astype(int),
            "is_holiday": [int((d.month, d.day) in HOLIDAYS) for d in days],
            "days_since_pay": np.minimum(since, 40),
            "days_to_pay": np.minimum(to, 40),
            "dow_ratio": [dow_ratio[d] for d in days.day_of_week],
            "lvl7_rel": lvl7 / base,
            "lvl90_rel": lvl90 / base,
        },
        index=days,
    )
    return X, base


# --- Обучение ---------------------------------------------------------------------------


def _training_rows(seed: int, end: date) -> tuple[list[pd.DataFrame], list[np.ndarray]]:
    from app.forecasting.data import history_from_synthetic
    from app.forecasting.engine import build_context
    from app.seed.synthetic import generate_profile, random_profile_spec

    profile = generate_profile(random_profile_spec(seed), end=end, seed=seed)
    all_h = history_from_synthetic(profile, end)
    xs, ys = [], []
    origin = profile.start + timedelta(days=100)
    while origin + timedelta(days=HORIZON_DAYS) <= end:
        h = History(all_h.txs[all_h.txs["date"] <= pd.Timestamp(origin)].copy(), origin, 0.0)
        ctx = build_context(h, origin + timedelta(days=HORIZON_DAYS), n_samples=1)
        X, base = make_features(ctx)

        # Факт: переменные траты в горизонте (без регулярных платежей, найденных на дату прогноза)
        future = all_h.txs[
            (all_h.txs["date"] > pd.Timestamp(origin))
            & (all_h.txs["date"] <= pd.Timestamp(ctx.horizon_end))
            & (all_h.txs["amount"] < 0)
            & (all_h.txs["kind"] == "expense")
        ]
        rec_keys = {r.key for r in ctx.recurring if r.amount < 0}
        future = future[~future["description"].map(description_key).isin(rec_keys)]
        actual = (-future.groupby("date")["amount"].sum()).reindex(X.index, fill_value=0.0)
        xs.append(X)
        ys.append(actual.to_numpy() / base)
        origin += timedelta(days=9)
    return xs, ys


def train(
    n_profiles: int = 40, *, end: date | None = None, n_estimators: int = 300, seed: int = 0
) -> dict:
    """Обучает модели среднего и квантилей на синтетических профилях."""
    started = time.perf_counter()
    end = end or date.today()
    xs, ys = [], []
    for i in range(n_profiles):
        x, y = _training_rows(TRAIN_SEED_OFFSET + seed * 1000 + i, end)
        xs += x
        ys += y
    X = pd.concat(xs)[FEATURES]
    y = np.clip(np.concatenate(ys), 0, 15)  # отсекаем редкие огромные покупки

    params = {
        "learning_rate": 0.05,
        "num_leaves": 15,
        "min_data_in_leaf": 40,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "feature_fraction": 0.9,
        "seed": seed,
        "verbose": -1,
    }
    data = lgb.Dataset(X, y, free_raw_data=False)
    models = {"mean": lgb.train({**params, "objective": "regression"}, data, n_estimators)}
    for q in QUANTILES:
        models[f"q{int(q * 100)}"] = lgb.train(
            {**params, "objective": "quantile", "alpha": q}, data, n_estimators
        )

    importance = models["mean"].feature_importance(importance_type="gain")
    top = sorted(zip(FEATURES, importance, strict=True), key=lambda p: -p[1])[:3]
    return {
        "meta": {
            "trained_at": date.today().isoformat(),
            "n_profiles": n_profiles,
            "n_rows": len(X),
            "train_seconds": round(time.perf_counter() - started, 1),
            "top_features": [name for name, _ in top],
        },
        "boosters": {k: m.model_to_string() for k, m in models.items()},
    }


def model_path() -> Path:
    return Path(get_settings().models_dir) / MODEL_FILE


def save_model(model: dict, path: Path | None = None) -> Path:
    path = path or model_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model), encoding="utf-8")
    return path


class LoadedModel:
    def __init__(self, raw: dict):
        self.meta = raw["meta"]
        self.boosters = {k: lgb.Booster(model_str=s) for k, s in raw["boosters"].items()}

    def predict(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        return {k: np.clip(b.predict(X[FEATURES]), 0, None) for k, b in self.boosters.items()}


# --- Стратегия --------------------------------------------------------------------------


def _fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def _sample_quantiles(
    q10: np.ndarray, q50: np.ndarray, q90: np.ndarray, rng: np.random.Generator, n: int
) -> np.ndarray:
    """Сценарии из кусочно-линейной функции распределения по квантилям."""
    q50 = np.maximum(q50, q10)
    q90 = np.maximum(q90, q50)
    upper = q90 + 2 * (q90 - q50)  # «хвост» крупных трат
    xp = np.array([0.0, 0.1, 0.5, 0.9, 1.0])
    fp = np.stack([np.zeros_like(q10), q10, q50, q90, upper])  # (5, days)
    u = rng.random((n, len(q10)))
    out = np.empty_like(u)
    for j in range(len(q10)):
        out[:, j] = np.interp(u[:, j], xp, fp[:, j])
    return out


class MLGBMStrategy:
    name = "ml_gbm"
    title = "H3 · ML (LightGBM)"
    description = (
        "Глобальная модель градиентного бустинга, обученная на синтетических профилях: "
        "календарь, зарплата, праздники; интервалы — квантильная регрессия."
    )

    def __init__(self, model: dict | None = None):
        self._model = LoadedModel(model) if model else None

    def _get_model(self) -> LoadedModel:
        if self._model is None:
            path = model_path()
            if not path.exists():
                # Первая загрузка без обученной модели — обучаем облегчённую версию на лету
                save_model(train(n_profiles=15, n_estimators=150), path)
            self._model = LoadedModel(json.loads(path.read_text(encoding="utf-8")))
        return self._model

    def predict(self, ctx: ForecastContext) -> StrategyOutput:
        model = self._get_model()
        X, base = make_features(ctx)
        pred = model.predict(X)
        daily_mean = pred["mean"] * base
        samples = _sample_quantiles(pred["q10"], pred["q50"], pred["q90"], ctx.rng, ctx.n_samples)
        samples *= base
        # Приводим среднее сценариев к прогнозу модели среднего
        col_mean = samples.mean(axis=0)
        samples *= np.divide(daily_mean, col_mean, out=np.ones_like(col_mean), where=col_mean > 0)

        # Разбивка по категориям — пропорционально тратам за последние 90 дней
        var = ctx.variable_expenses()
        recent = var[var["date"] > pd.Timestamp(ctx.history.as_of - timedelta(days=90))]
        shares = recent.groupby("category")["spend"].sum()
        total = float(daily_mean.sum())
        by_category = (
            {str(c): float(v) / float(shares.sum()) * total for c, v in shares.items()}
            if shares.sum() > 0
            else {"other": total}
        )

        extra_mean, extra_samples = StatisticalStrategy._irregular_income(ctx, len(ctx.days))
        return StrategyOutput(
            daily_mean=daily_mean,
            samples=samples,
            by_category=by_category,
            extra_income_mean=extra_mean,
            extra_income_samples=extra_samples,
            explanation=(
                f"ML-модель ожидает переменные траты около {_fmt(daily_mean.mean())} ₽ в день "
                f"(ваш обычный уровень — {_fmt(base)} ₽). Важнее всего для модели: "
                + ", ".join(FEATURE_TITLES[f] for f in model.meta["top_features"])
                + "."
            ),
            meta={"ml_model": model.meta},
        )
