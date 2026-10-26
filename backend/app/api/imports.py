import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.importers.statement import PRESETS, ColumnMapping, StatementError
from app.models import ImportJob
from app.schemas.imports import ImportConfirm, ImportJobOut, ImportPreview, ImportResult
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
