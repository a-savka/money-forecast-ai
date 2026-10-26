"""MOCK: подключение банка.

В реальной версии здесь будет Open Banking / API банков-партнёров (OAuth-согласие,
получение счетов и операций). Сейчас операции генерируются синтетическим профилем,
детерминированно для пары «пользователь + банк».
"""

import zlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, ImportJob, User
from app.seed.synthetic import generate_profile, random_profile_spec
from app.services.imports import NewTransaction, insert_transactions


@dataclass(frozen=True)
class MockBank:
    key: str
    name: str
    color: str
    card_name: str


BANKS: dict[str, MockBank] = {
    b.key: b
    for b in [
        MockBank("tbank", "Т-Банк", "#ffdd2d", "Т-Банк Black"),
        MockBank("sber", "Сбер", "#21a038", "СберКарта"),
        MockBank("alfa", "Альфа-Банк", "#ef3124", "Альфа-Карта"),
        MockBank("vtb", "ВТБ", "#0a2896", "Мультикарта ВТБ"),
        MockBank("ozon", "Озон Банк", "#005bff", "Озон Карта"),
    ]
}


def connect_bank(
    db: Session, user: User, bank_key: str, months: int = 6, end: date | None = None
) -> tuple[Account, int]:
    bank = BANKS[bank_key]
    seed = zlib.crc32(f"{user.id}:{bank_key}".encode())
    profile = generate_profile(random_profile_spec(seed), end=end, months=months, seed=seed)

    account = Account(
        user_id=user.id,
        name=bank.card_name,
        bank_name=bank.name,
        source="bank_mock",
        balance_initial=sum(profile.balances_initial, Decimal(0)),
    )
    db.add(account)
    db.flush()
    job = ImportJob(
        user_id=user.id, account_id=account.id, type="bank_mock", status="done", file_name=bank.name
    )
    db.add(job)
    db.flush()

    rows = [NewTransaction(t.date, t.amount, t.description, t.mcc) for t in profile.transactions]
    imported, skipped = insert_transactions(
        db, user, account, rows, source="bank_mock", import_job=job
    )
    job.rows_total = len(rows)
    job.rows_imported = imported
    job.rows_skipped = skipped
    db.commit()
    return account, imported
