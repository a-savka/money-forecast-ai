from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.categorizer.service import Categorizer
from app.importers.statement import PRESETS, ColumnMapping, parse_statement
from app.models import Account, ImportJob, Transaction, User
from app.schemas.imports import ImportPreview, PreviewRow
from app.services.demo_data import tx_hash


@dataclass
class NewTransaction:
    date: date
    amount: Decimal
    description: str
    mcc: str | None = None
    bank_category: str | None = None


def with_hashes(rows: list[NewTransaction]) -> list[tuple[NewTransaction, str]]:
    """Хэш для дедупликации: дата + сумма + описание + номер повтора внутри файла.

    Две одинаковые покупки кофе в один день остаются двумя операциями,
    а повторная загрузка того же файла ничего не дублирует.
    """
    seen: Counter[tuple] = Counter()
    out = []
    for r in rows:
        key = (r.date, r.amount, r.description.strip().lower())
        out.append((r, tx_hash(r.date, r.amount, r.description, seen[key])))
        seen[key] += 1
    return out


def existing_hashes(db: Session, user: User) -> set[str]:
    return set(
        db.scalars(
            select(Transaction.dedup_hash).where(
                Transaction.user_id == user.id, Transaction.dedup_hash.is_not(None)
            )
        )
    )


def insert_transactions(
    db: Session,
    user: User,
    account: Account,
    rows: list[NewTransaction],
    *,
    source: str,
    import_job: ImportJob | None = None,
) -> tuple[int, int]:
    """Категоризирует и сохраняет операции, пропуская дубли. Возвращает (добавлено, пропущено)."""
    categorizer = Categorizer(db, user)
    known = existing_hashes(db, user)
    imported = skipped = 0
    for row, h in with_hashes(rows):
        if h in known:
            skipped += 1
            continue
        guess = categorizer.categorize(
            row.description, float(row.amount), row.mcc, row.bank_category
        )
        db.add(
            Transaction(
                user_id=user.id,
                account_id=account.id,
                date=row.date,
                amount=row.amount,
                description=row.description,
                merchant=row.description if row.mcc else None,
                mcc=row.mcc,
                category_id=guess.category_id,
                category_source=guess.source,
                source=source,
                dedup_hash=h,
                import_job_id=import_job.id if import_job else None,
            )
        )
        known.add(h)
        imported += 1
    return imported, skipped


def preview_statement(
    db: Session, user: User, content: bytes, filename: str, mapping: ColumnMapping | None
) -> ImportPreview:
    parsed = parse_statement(content, filename, mapping)
    rows = [
        NewTransaction(r.date, r.amount, r.description, r.mcc, r.bank_category) for r in parsed.rows
    ]
    known = existing_hashes(db, user)
    hashed = with_hashes(rows)
    categorizer = Categorizer(db, user)
    preset = PRESETS.get(parsed.preset) if parsed.preset else None

    job = None
    if rows:
        job = ImportJob(
            user_id=user.id,
            type="csv",
            status="preview",
            file_name=filename,
            rows_total=len(rows),
            errors=parsed.errors,
            payload={
                "bank_name": preset.bank_name if preset else None,
                "rows": [
                    {
                        "date": r.date.isoformat(),
                        "amount": str(r.amount),
                        "description": r.description,
                        "mcc": r.mcc,
                        "bank_category": r.bank_category,
                    }
                    for r in rows
                ],
            },
        )
        db.add(job)
        db.commit()

    sample = []
    for (row, h), parsed_row in list(zip(hashed, parsed.rows, strict=True))[:30]:
        guess = categorizer.categorize(
            row.description, float(row.amount), row.mcc, row.bank_category
        )
        sample.append(
            PreviewRow(
                line=parsed_row.line,
                date=row.date,
                amount=float(row.amount),
                description=row.description,
                category_id=guess.category_id,
                duplicate=h in known,
            )
        )

    dates = [r.date for r in rows]
    return ImportPreview(
        job_id=job.id if job else None,
        file_name=filename,
        headers=parsed.headers,
        mapping=parsed.mapping,
        preset=parsed.preset,
        bank_name=preset.bank_name if preset else None,
        rows_total=len(rows),
        duplicates=sum(h in known for _, h in hashed),
        skipped=parsed.skipped,
        errors=parsed.errors[:20],
        period_start=min(dates) if dates else None,
        period_end=max(dates) if dates else None,
        total_income=float(sum((r.amount for r in rows if r.amount > 0), Decimal(0))),
        total_expense=float(sum((r.amount for r in rows if r.amount < 0), Decimal(0))),
        sample=sample,
    )


def confirm_import(
    db: Session,
    user: User,
    job: ImportJob,
    account_id: int | None,
    new_account_name: str | None,
) -> tuple[Account, int, int]:
    payload = job.payload or {}
    if account_id is not None:
        account = db.get(Account, account_id)
        if account is None or account.user_id != user.id:
            raise ValueError("Счёт не найден")
    else:
        bank = payload.get("bank_name")
        account = Account(
            user_id=user.id,
            name=new_account_name or (f"Карта {bank}" if bank else "Импортированный счёт"),
            bank_name=bank,
            source="csv",
        )
        db.add(account)
        db.flush()

    rows = [
        NewTransaction(
            date=date.fromisoformat(r["date"]),
            amount=Decimal(r["amount"]),
            description=r["description"],
            mcc=r.get("mcc"),
            bank_category=r.get("bank_category"),
        )
        for r in payload.get("rows", [])
    ]
    imported, skipped = insert_transactions(db, user, account, rows, source="csv", import_job=job)
    job.account_id = account.id
    job.status = "done"
    job.rows_imported = imported
    job.rows_skipped = skipped
    job.payload = None  # сырые строки больше не нужны
    db.commit()
    return account, imported, skipped
