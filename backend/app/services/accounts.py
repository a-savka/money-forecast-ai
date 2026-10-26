from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, Transaction, User


def account_balances(db: Session, user: User) -> dict[int, Decimal]:
    """Текущий баланс каждого счёта = начальный + сумма операций."""
    sums = dict(
        db.execute(
            select(Transaction.account_id, func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.user_id == user.id)
            .group_by(Transaction.account_id)
        ).all()
    )
    accounts = db.scalars(select(Account).where(Account.user_id == user.id)).all()
    return {a.id: Decimal(a.balance_initial) + Decimal(str(sums.get(a.id, 0))) for a in accounts}


def get_or_create_default_account(db: Session, user: User) -> Account:
    acc = db.scalar(select(Account).where(Account.user_id == user.id).order_by(Account.id))
    if acc is None:
        acc = Account(user_id=user.id, name="Наличные", type="cash", source="manual")
        db.add(acc)
        db.flush()
    return acc
