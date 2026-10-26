from datetime import date, timedelta
from decimal import Decimal

from app.models import Account, Category, Transaction, User
from app.services.budgets import budget_statuses, suggest_limits, upsert_budget

TODAY = date(2026, 10, 20)


def _setup(db):
    user = User(email="b@t.c", name="B")
    db.add(user)
    db.flush()
    acc = Account(user_id=user.id, name="Карта", balance_initial=Decimal(0))
    db.add(acc)
    db.flush()
    cafe = db.query(Category).filter_by(slug="cafe").one()

    def tx(d, amount):
        db.add(
            Transaction(
                user_id=user.id,
                account_id=acc.id,
                date=d,
                amount=Decimal(amount),
                description="Кафе",
                category_id=cafe.id,
                dedup_hash=f"{d}{amount}{id(d)}",
            )
        )

    # История: 3 месяца по 300 ₽ в день → ≈ 9 000 ₽ в месяц
    for i in range(1, 91):
        tx(TODAY.replace(day=1) - timedelta(days=i), -300)
    # Текущий месяц: потрачено 6 000 ₽ за 20 дней
    for d in range(1, 21):
        tx(TODAY.replace(day=d), -300)
    db.commit()
    return user, cafe


def test_status_and_exhaustion(db):
    user, cafe = _setup(db)
    upsert_budget(db, user, cafe.id, Decimal(8000))
    (s,) = budget_statuses(db, user, TODAY)
    assert s.spent == 6000 and s.remaining == 2000
    assert s.daily_pace == 300
    assert s.exhausted_in_days == 6  # 2000 / 300
    assert s.status == "warning"  # закончится раньше конца месяца (через 11 дней)
    assert s.projected == 6000 + 300 * 11

    upsert_budget(db, user, cafe.id, Decimal(20000))
    (s,) = budget_statuses(db, user, TODAY)
    assert s.status == "ok"
    upsert_budget(db, user, cafe.id, Decimal(5000))
    (s,) = budget_statuses(db, user, TODAY)
    assert s.status == "over" and s.exhausted_in_days == 0


def test_suggest(db):
    user, cafe = _setup(db)
    assert suggest_limits(db, user, TODAY) == {cafe.id: 9000.0}


def test_api_free_limit(client, auth):
    cats = client.get("/categories", headers=auth).json()
    expense = [c for c in cats if c["kind"] == "expense"]
    income = next(c for c in cats if c["kind"] == "income")
    put = lambda cid, v: client.put(  # noqa: E731
        "/mock/budgets", json={"category_id": cid, "limit": v}, headers=auth
    )
    assert put(income["id"], 1000).status_code == 422
    r = put(expense[0]["id"], 5000)
    assert r.status_code == 200 and len(r.json()) == 1
    assert put(expense[0]["id"], 6000).json()[0]["limit"] == 6000  # обновление — можно
    assert put(expense[1]["id"], 5000).status_code == 402  # второй лимит в Free — нельзя
    client.post("/mock/subscription", json={"action": "start_trial"}, headers=auth)
    assert len(put(expense[1]["id"], 5000).json()) == 2
    assert client.get("/mock/budgets/suggest", headers=auth).json()
    bid = client.get("/mock/budgets", headers=auth).json()[0]["id"]
    assert len(client.delete(f"/mock/budgets/{bid}", headers=auth).json()) == 1
