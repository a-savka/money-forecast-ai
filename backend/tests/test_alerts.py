from datetime import date

from app.forecasting.schemas import CashGap, ForecastResult, UpcomingPayment
from app.services.alerts import build_alerts

TODAY = date(2026, 10, 26)


def _forecast(risk: str) -> ForecastResult:
    return ForecastResult(
        strategy="statistical",
        as_of=TODAY,
        period_end=date(2026, 11, 2),
        current_balance=1000,
        expected_expense=5000,
        expected_expense_p10=4000,
        expected_expense_p90=6000,
        expected_income=0,
        expected_balance_end=-4000,
        by_category=[],
        daily_balance=[],
        upcoming=[
            UpcomingPayment(
                date=date(2026, 10, 27),
                name="Аренда",
                category="rent",
                amount=-30000,
                confidence=0.9,
            ),
            UpcomingPayment(
                date=date(2026, 10, 27),
                name="Музыка",
                category="subscriptions",
                amount=-199,
                confidence=0.9,
            ),
        ],
        cash_gap=CashGap(
            risk=risk, probability=0.6, first_negative_date=date(2026, 10, 28), min_balance_p10=-1
        ),
        safe_to_spend_per_day=0,
    )


def test_gap_and_payment_alerts(db):
    from app.models import User

    user = User(email="a@l.c", name="A")
    db.add(user)
    db.commit()
    alerts = build_alerts(db, user, _forecast("high"), TODAY)
    kinds = [a.kind for a in alerts]
    assert kinds == ["cash_gap", "payment"]  # мелкий платёж не тревожим
    assert alerts[0].severity == "critical" and "28 октября" in alerts[0].body
    assert build_alerts(db, user, _forecast("low"), TODAY)[0].kind == "payment"


def test_api(client, auth):
    r = client.get("/mock/notifications", headers=auth)
    assert r.status_code == 200 and isinstance(r.json(), list)
    assert client.post("/mock/push/test", headers=auth).json()["kind"] == "test"
