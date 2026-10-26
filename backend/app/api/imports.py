import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import select

from app.categorizer.service import Categorizer
from app.deps import CurrentUser, DbSession
from app.importers.receipt import ReceiptError, parse_receipt_qr
from app.importers.statement import PRESETS, ColumnMapping, StatementError
from app.models import ImportJob
from app.schemas.imports import (
    BankConnectRequest,
    BankConnectResult,
    ImportConfirm,
    ImportJobOut,
    ImportPreview,
    ImportResult,
    MockBankOut,
    ReceiptQRRequest,
    TransactionDraft,
)
from app.services.bank_mock import BANKS, connect_bank
from app.services.categories import category_ids_by_slug
from app.services.imports import confirm_import, preview_statement

router = APIRouter(prefix="/imports", tags=["imports"])

MAX_FILE_SIZE = 5 * 1024 * 1024


@router.get("/presets")
def list_presets() -> list[dict[str, str]]:
    return [{"key": p.key, "title": p.title, "bank_name": p.bank_name} for p in PRESETS.values()]


@router.post("/statement")
async def upload_statement(
    user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File()],
    mapping: Annotated[str | None, Form(description="JSON ColumnMapping")] = None,
) -> ImportPreview:
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Файл больше 5 МБ")
    try:
        column_mapping = ColumnMapping.model_validate(json.loads(mapping)) if mapping else None
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(422, "Некорректное сопоставление колонок") from exc
    try:
        return preview_statement(
            db, user, content, file.filename or "statement.csv", column_mapping
        )
    except StatementError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{job_id}/confirm")
def confirm(job_id: int, body: ImportConfirm, user: CurrentUser, db: DbSession) -> ImportResult:
    job = db.get(ImportJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(404, "Импорт не найден")
    if job.status != "preview":
        raise HTTPException(409, "Импорт уже выполнен")
    try:
        account, imported, skipped = confirm_import(
            db, user, job, body.account_id, body.new_account_name
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ImportResult(job_id=job.id, account_id=account.id, imported=imported, skipped=skipped)


@router.get("")
def list_imports(user: CurrentUser, db: DbSession) -> list[ImportJobOut]:
    jobs = db.scalars(
        select(ImportJob)
        .where(ImportJob.user_id == user.id)
        .order_by(ImportJob.id.desc())
        .limit(20)
    )
    return [ImportJobOut.model_validate(j) for j in jobs]


@router.get("/bank-mock/banks")
def list_banks() -> list[MockBankOut]:
    return [MockBankOut(key=b.key, name=b.name, color=b.color) for b in BANKS.values()]


@router.post("/bank-mock/connect")
def connect(body: BankConnectRequest, user: CurrentUser, db: DbSession) -> BankConnectResult:
    """MOCK: «подключение» банка — генерирует историю операций за N месяцев."""
    if body.bank not in BANKS:
        raise HTTPException(404, "Банк не поддерживается")
    account, imported = connect_bank(db, user, body.bank, body.months)
    return BankConnectResult(account_id=account.id, account_name=account.name, imported=imported)


@router.post("/receipt/qr")
def receipt_qr(body: ReceiptQRRequest, user: CurrentUser, db: DbSession) -> TransactionDraft:
    try:
        receipt = parse_receipt_qr(body.qr)
    except ReceiptError as exc:
        raise HTTPException(422, str(exc)) from exc
    description = f"Покупка по чеку №{receipt.fd}" if receipt.fd else "Покупка по чеку"
    guess = Categorizer(db, user).categorize(description, float(receipt.amount))
    # Большинство бумажных чеков — из продуктовых магазинов; пользователь может поменять
    category_id = guess.category_id
    if guess.source == "default" and receipt.amount < 0:
        category_id = category_ids_by_slug(db)["products"]
    return TransactionDraft(
        date=receipt.timestamp.date(),
        amount=float(receipt.amount),
        description=description,
        category_id=category_id,
        source="receipt",
    )
