from datetime import date

import pytest

from app.models import User
from app.services import subscription as sub

TODAY = date(2026, 10, 26)


def test_plan_lifecycle():
    u = User(email="a@b.c", name="A", is_premium=False)
    assert sub.plan(u, TODAY) == "free"
    sub.start_trial(u, TODAY)
    assert sub.plan(u, TODAY) == "trial" and u.trial_until == date(2026, 11, 1)
    assert sub.plan(u, date(2026, 11, 2)) == "free"  # триал закончился
    with pytest.raises(ValueError):
        sub.start_trial(u, TODAY)  # второй раз нельзя
    sub.upgrade(u)
    assert sub.plan(u, date(2027, 1, 1)) == "premium"
    sub.cancel(u, TODAY)
    assert sub.plan(u, TODAY) == "free"


def test_paywall_on_month_forecast(client, auth):
    assert client.get("/mock/subscription", headers=auth).json()["plan"] == "free"
    r = client.get("/forecast", params={"horizon": "month"}, headers=auth)
    assert r.status_code == 402
    # По умолчанию Free получает недельный прогноз
    assert len(client.get("/forecast", headers=auth).json()["daily_balance"]) == 7

    body = client.post("/mock/subscription", json={"action": "start_trial"}, headers=auth).json()
    assert body["plan"] == "trial" and body["trial_days_left"] == 7
    assert not body["can_start_trial"]
    assert client.get("/forecast", params={"horizon": "month"}, headers=auth).status_code == 200
    again = client.post("/mock/subscription", json={"action": "start_trial"}, headers=auth)
    assert again.status_code == 409

    body = client.post("/mock/subscription", json={"action": "cancel"}, headers=auth).json()
    assert body["plan"] == "free"
    assert client.get("/auth/me", headers=auth).json()["is_premium"] is False
