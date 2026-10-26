import hashlib
from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Account, ImportJob, Transaction, User
from app.seed.synthetic import PROFILES, SyntheticProfile, generate_profile
from app.services.categories import category_ids_by_slug


def tx_hash(d: date, amount: object, description: str, salt: object = "") -> str:
    raw = f"{d.isoformat()}|{amount}|{description.strip().lower()}|{salt}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def clear_user_data(db: Session, user: User) -> None:
    db.execute(delete(Transaction).where(Transaction.user_id == user.id))
    db.execute(delete(ImportJob).where(ImportJob.user_id == user.id))
    db.execute(delete(Account).where(Account.user_id == user.id))
    db.flush()


def load_synthetic_profile(
    db: Session,
    user: User,
    profile: str | SyntheticProfile,
    *,
    end: date | None = None,
    months: int = 12,
    seed: int = 42,
    source: str = "bank_mock",
) -> list[Account]:
    """Заливает синтетическую историю операций в БД пользователя."""
    if isinstance(profile, str):
        if profile not in PROFILES:
            raise ValueError(f"Unknown profile: {profile}")
        profile = generate_profile(profile, end=end, months=months, seed=seed)
    cats = category_ids_by_slug(db)

    accounts = []
    for spec, balance in zip(profile.spec.accounts, profile.balances_initial, strict=True):
        acc = Account(
            user_id=user.id,
            name=spec.name,
            bank_name=spec.bank_name,
            source=source,
            balance_initial=balance,
        )
        db.add(acc)
        accounts.append(acc)
    db.flush()

    for i, t in enumerate(profile.transactions):
        db.add(
            Transaction(
                user_id=user.id,
                account_id=accounts[t.account].id,
                date=t.date,
                amount=t.amount,
                description=t.description,
                merchant=t.description if t.mcc else None,
                mcc=t.mcc,
                category_id=cats[t.category],
                category_source="bank",
                source=source,
                dedup_hash=tx_hash(t.date, t.amount, t.description, i),
                is_recurring=t.is_recurring,
            )
        )
    db.commit()
    return accounts
