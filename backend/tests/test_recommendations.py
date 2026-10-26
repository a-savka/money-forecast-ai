from datetime import date

from app.forecasting.data import history_from_synthetic
from app.forecasting.engine import run_forecast
from app.forecasting.recommendations import llm_recommendations, rule_recommendations
from app.forecasting.strategies.statistical import StatisticalStrategy
from app.seed.synthetic import generate_profile

AS_OF = date(2026, 10, 26)
END = date(2026, 11, 30)


def _recs(profile):
    h = history_from_synthetic(generate_profile(profile, end=AS_OF), AS_OF)
    f = run_forecast(StatisticalStrategy(), h, END, n_samples=300)
    return f, rule_recommendations(f, h)


def test_cash_gap_recommends_cuts():
    f, recs = _recs("freelancer")
    assert f.cash_gap.risk in ("medium", "high")
    cuts = [r for r in recs if r.type == "cash_gap" and r.id != "gap-topup"]
    assert cuts and all(r.amount_effect > 0 and r.category for r in cuts)
    assert recs[0].type == "cash_gap"  # самое важное — первым


def test_low_risk_suggests_saving_and_subscriptions():
    f, recs = _recs("young")
    assert f.cash_gap.risk == "low"
    types = {r.type for r in recs}
    assert "save" in types and "subscriptions" in types


def test_llm_mode_keeps_numbers():
    f, recs = _recs("dropout")
    out, info = llm_recommendations(recs, f, "mock")
    assert info["llm_provider"] == "mock"
    assert [r.amount_effect for r in out] == [r.amount_effect for r in recs]
    assert all(r.source == "llm" for r in out)


def test_api(client, auth):
    body = client.get("/recommendations", headers=auth).json()
    assert body["mode"] == "rules" and body["items"]
    assert client.get("/recommendations", params={"mode": "llm"}, headers=auth).status_code == 200
