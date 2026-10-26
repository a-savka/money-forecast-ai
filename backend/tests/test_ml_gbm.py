from datetime import date

import numpy as np

from app.forecasting.data import history_from_synthetic
from app.forecasting.engine import build_context, run_forecast
from app.forecasting.strategies.ml_gbm import (
    FEATURES,
    MLGBMStrategy,
    _sample_quantiles,
    make_features,
    save_model,
)
from app.seed.synthetic import generate_profile

AS_OF = date(2026, 10, 12)
END = date(2026, 10, 31)


def test_features_shape_and_paydays():
    h = history_from_synthetic(generate_profile("young", end=AS_OF), AS_OF)
    ctx = build_context(h, END, n_samples=10)
    X, base = make_features(ctx)
    assert list(X.columns) == FEATURES and len(X) == len(ctx.days)
    assert base > 0
    assert X["days_since_pay"].min() == 0  # в горизонте есть зарплата
    assert X["step"].iloc[0] == 1


def test_model_metadata(tiny_ml_model):
    assert set(tiny_ml_model["boosters"]) == {"mean", "q10", "q50", "q90"}
    assert tiny_ml_model["meta"]["n_rows"] > 0
    assert set(tiny_ml_model["meta"]["top_features"]) <= set(FEATURES)


def test_forecast_with_model(tiny_ml_model):
    h = history_from_synthetic(generate_profile("dropout", end=AS_OF), AS_OF)
    r = run_forecast(MLGBMStrategy(tiny_ml_model), h, END, n_samples=200)
    assert r.strategy == "ml_gbm"
    assert r.expected_expense > 0
    assert r.model_info["ml_model"]["n_profiles"] == 2
    assert "ML-модель" in r.explanation


def test_save_and_load(tmp_path, tiny_ml_model):
    path = save_model(tiny_ml_model, tmp_path / "m.json")
    assert path.exists()


def test_quantile_sampling_is_monotonic():
    rng = np.random.default_rng(0)
    q10, q50, q90 = np.array([0.0, 100]), np.array([50.0, 200]), np.array([150.0, 400])
    s = _sample_quantiles(q10, q50, q90, rng, 5000)
    assert s.min() >= 0
    assert np.allclose(np.percentile(s, 50, axis=0), q50, rtol=0.1)
    assert (np.percentile(s, 90, axis=0) <= q90 * 1.1).all()
