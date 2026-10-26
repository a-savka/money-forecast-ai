from datetime import date

from app.models import User
from app.services.analytics import dynamics, month_summary
from app.services.demo_data import load_synthetic_profile


def _user(db, profile="young"):
    user = User(email=f"{profile}@a.ru", name="A")
    db.add(user)
    db.commit()
    load_synthetic_profile(db, user, profile, end=date(2026, 10, 26))
    return user


def test_month_summary(db):
    user = _user(db)
    s = month_summary(db, user, 2026, 9, today=date(2026, 10, 26))
    assert s.days_elapsed == 30
    assert s.income == 90000
    assert s.expense > 30000
    assert abs(sum(c.share for c in s.by_category) - 1) < 1e-6
    assert s.by_category[0].amount >= s.by_category[-1].amount
    # Переводы на накопительный счёт не считаются расходом
    assert all(c.amount < s.expense for c in s.by_category)


def test_current_month_compares_same_days(db):
    user = _user(db)
    s = month_summary(db, user, 2026, 10, today=date(2026, 10, 12))
    assert s.days_elapsed == 12
    full_prev = month_summary(db, user, 2026, 9, today=date(2026, 10, 12)).expense
    assert s.prev_expense < full_prev


def test_dynamics(db, client, auth):
    user = _user(db, "family")
    pts = dynamics(db, user, 6, date(2026, 10, 26))
    assert [p.month for p in pts] == [
        "2026-05",
        "2026-06",
        "2026-07",
        "2026-08",
        "2026-09",
        "2026-10",
    ]
    assert all(p.income > 0 for p in pts)
    assert (
        client.get("/analytics/summary", params={"month": "2026-13"}, headers=auth).status_code
        == 422
    )
    assert client.get("/analytics/dynamics", headers=auth).status_code == 200
