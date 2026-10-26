"""Построение History из БД пользователя или из синтетического профиля (для бэктеста)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.forecasting.base import History
from app.models import Account, Category, Transaction, User
from app.seed.synthetic import SyntheticProfile
from app.services.categories import SYSTEM_CATEGORIES

KIND_BY_SLUG = {c.slug: c.kind for c in SYSTEM_CATEGORIES}


def history_from_db(db: Session, user: User, as_of: date) -> History:
    rows = db.execute(
        select(
            Transaction.date,
            Transaction.amount,
            func.coalesce(Category.slug, "other"),
            func.coalesce(Category.kind, "expense"),
            Transaction.description,
        )
        .join(Category, Category.id == Transaction.category_id, isouter=True)
        .where(Transaction.user_id == user.id, Transaction.date <= as_of)
        .order_by(Transaction.date)
    ).all()
    initial = db.scalar(
        select(func.coalesce(func.sum(Account.balance_initial), 0)).where(
            Account.user_id == user.id
        )
    )
    balance = Decimal(str(initial)) + sum((Decimal(r[1]) for r in rows), Decimal(0))
    records = [
        {"date": d, "amount": float(a), "category": c, "kind": k, "description": desc}
        for d, a, c, k, desc in rows
    ]
    return History.from_records(records, as_of, float(balance))


def history_from_synthetic(profile: SyntheticProfile, as_of: date) -> History:
    txs = [t for t in profile.transactions if t.date <= as_of]
    records = [
        {
            "date": t.date,
            "amount": float(t.amount),
            "category": t.category,
            "kind": KIND_BY_SLUG.get(t.category, "expense"),
            "description": t.description,
        }
        for t in txs
    ]
    balance = float(sum(profile.balances_initial)) + sum(float(t.amount) for t in txs)
    return History.from_records(records, as_of, balance)
