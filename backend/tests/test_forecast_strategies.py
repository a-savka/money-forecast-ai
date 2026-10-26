from datetime import date

import pytest

from app.forecasting.data import history_from_synthetic
from app.forecasting.engine import month_end, run_forecast
from app.forecasting.registry import STRATEGIES
from app.seed.synthetic import PROFILES, generate_profile

AS_OF = date(2026, 10, 12)


def actual_expense(profile, as_of, end):
    return -sum(
        float(t.amount)
        for t in profile.transactions
        if as_of < t.date <= end and t.amount < 0 and t.category != "savings"
    )


@pytest.fixture(scope="module")
def profiles():
    return {k: generate_profile(k, end=date(2026, 10, 31)) for k in PROFILES}


@pytest.mark.parametrize("strategy", list(STRATEGIES))
@pytest.mark.parametrize("key", list(PROFILES))
def test_result_is_consistent(profiles, strategy, key):
    h = history_from_synthetic(profiles[key], AS_OF)
    r = run_forecast(STRATEGIES[strategy], h, month_end(AS_OF), n_samples=200)
    assert r.as_of == AS_OF and r.period_end == date(2026, 10, 31)
    assert len(r.daily_balance) == 19
    assert r.expected_expense_p10 <= r.expected_expense_p90
    assert all(p.p10 <= p.p50 <= p.p90 for p in r.daily_balance)
    assert r.cash_gap.risk in {"low", "medium", "high"}
    assert 0 <= r.cash_gap.probability <= 1
    assert r.safe_to_spend_per_day >= 0
    assert r.explanation


@pytest.mark.parametrize("key", list(PROFILES))
def test_statistical_is_reasonably_accurate(profiles, key):
    p = profiles[key]
    h = history_from_synthetic(p, AS_OF)
    r = run_forecast(STRATEGIES["statistical"], h, month_end(AS_OF), n_samples=200)
    fact = actual_expense(p, AS_OF, month_end(AS_OF))
    assert abs(r.expected_expense - fact) / fact < 0.35


def test_statistical_schedules_known_payments(profiles):
    h = history_from_synthetic(profiles["young"], AS_OF)
    r = run_forecast(STRATEGIES["statistical"], h, month_end(AS_OF), n_samples=100)
    names = {u.name for u in r.upcoming}
    assert "КИНОПОИСК" in names  # 21-го числа
    assert any(u.amount > 0 for u in r.upcoming)  # аванс


def test_forecast_api(client, auth):
    strategies = client.get("/forecast/strategies").json()
    assert {s["name"] for s in strategies} == set(STRATEGIES)
    r = client.get("/forecast", params={"horizon": "week"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body["daily_balance"]) == 7
    assert client.get("/forecast", params={"strategy": "nope"}, headers=auth).status_code == 404


def test_forecast_requires_data(client):
    token = client.post("/auth/demo-login", json={}).json()["access_token"]
    r = client.get("/forecast", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 409


def test_horizon_end():
    from app.api.forecast import horizon_end

    assert horizon_end(date(2026, 10, 12), "month") == date(2026, 10, 31)
    assert horizon_end(date(2026, 10, 26), "month") == date(2026, 11, 30)
    assert horizon_end(date(2026, 10, 26), "week") == date(2026, 11, 2)
