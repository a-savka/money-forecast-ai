from datetime import date

import pytest

from app.forecasting.data import history_from_synthetic
from app.forecasting.engine import build_context, month_end, run_forecast
from app.forecasting.strategies import stat_llm
from app.forecasting.strategies.stat_llm import StatLLMStrategy, build_payload
from app.forecasting.strategies.statistical import StatisticalStrategy
from app.llm.base import LLMError, RawCompletion
from app.seed.synthetic import generate_profile

AS_OF = date(2026, 10, 12)


@pytest.fixture(scope="module")
def history():
    return history_from_synthetic(generate_profile("dropout", end=date(2026, 10, 31)), AS_OF)


def test_payload_has_only_aggregates(history):
    ctx = build_context(history, month_end(AS_OF), n_samples=50)
    out = StatisticalStrategy().predict(ctx)
    payload = build_payload(ctx, out.meta["categories"], out.meta["per_category_daily"])
    text = str(payload)
    assert "ПЯТЁРОЧКА" not in text and "WILDBERRIES" not in text  # описаний операций нет
    assert payload["holidays_in_horizon"] == []
    assert {"slug", "forecast", "trend_2w_vs_avg"} <= payload["categories"][0].keys()
    nov = build_context(history, date(2026, 11, 30), n_samples=10)
    out2 = StatisticalStrategy().predict(nov)
    p2 = build_payload(nov, out2.meta["categories"], out2.meta["per_category_daily"])
    assert p2["holidays_in_horizon"] == ["День народного единства"]


def test_mock_llm_adjusts_and_reports(history):
    r = run_forecast(StatLLMStrategy("mock"), history, date(2026, 11, 30), n_samples=100)
    info = r.model_info
    assert info["llm_provider"] == "mock"
    assert info["prompt"] == "forecast_adjust_v1"
    assert all(0.7 <= a["factor"] <= 1.3 for a in info["llm_adjustments"])
    h1 = run_forecast(StatisticalStrategy(), history, date(2026, 11, 30), n_samples=100)
    if info["llm_adjustments"]:
        assert r.expected_expense != h1.expected_expense


class BrokenProvider:
    name = "broken"
    model = "x"

    def complete(self, system, user, *, schema=None):
        return RawCompletion("я не умею в JSON")

    def complete_with_image(self, *a, **k):
        raise LLMError("no")


def test_fallback_to_h1(history, monkeypatch):
    monkeypatch.setattr(stat_llm, "get_provider", lambda name=None: BrokenProvider())
    r = run_forecast(StatLLMStrategy(), history, month_end(AS_OF), n_samples=100, seed=1)
    h1 = run_forecast(StatisticalStrategy(), history, month_end(AS_OF), n_samples=100, seed=1)
    assert r.model_info["llm_fallback"] is True
    assert r.expected_expense == h1.expected_expense
    assert "LLM недоступна" in r.explanation
