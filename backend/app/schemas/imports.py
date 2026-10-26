import datetime as dt

from pydantic import BaseModel

from app.importers.statement import ColumnMapping
from app.schemas.common import ORMModel


class PreviewRow(BaseModel):
    line: int
    date: dt.date
    amount: float
    description: str
    category_id: int | None
    duplicate: bool


class ImportPreview(BaseModel):
    job_id: int | None
    file_name: str
    headers: list[str]
    mapping: ColumnMapping | None
    preset: str | None
    bank_name: str | None
    rows_total: int
    duplicates: int
    skipped: int
    errors: list[str]
    period_start: dt.date | None
    period_end: dt.date | None
    total_income: float
    total_expense: float
    sample: list[PreviewRow]


class ImportConfirm(BaseModel):
    account_id: int | None = None
    new_account_name: str | None = None


class ImportResult(BaseModel):
    job_id: int
    account_id: int
    imported: int
    skipped: int


class ImportJobOut(ORMModel):
    id: int
    type: str
    status: str
    file_name: str | None
    rows_total: int
    rows_imported: int
    rows_skipped: int
    created_at: dt.datetime
