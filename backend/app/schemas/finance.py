import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class CategoryOut(ORMModel):
    id: int
    slug: str
    name: str
    kind: str
    icon: str
    color: str
    is_discretionary: bool


class CategorySuggestion(BaseModel):
    category: CategoryOut
    source: str


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    bank_name: str | None = None
    type: str = "card"
    balance_initial: float = 0


class AccountOut(ORMModel):
    id: int
    name: str
    bank_name: str | None
    type: str
    source: str
    balance_initial: float
    balance: float = 0
    currency: str


class TransactionIn(BaseModel):
    account_id: int | None = None
    date: dt.date
    # Расход < 0, доход > 0
    amount: float
    description: str = ""
    category_id: int | None = None
    mcc: str | None = Field(default=None, max_length=4)
    source: Literal["manual", "receipt", "screenshot"] = "manual"

    @field_validator("amount")
    @classmethod
    def non_zero(cls, v: float) -> float:
        if v == 0:
            raise ValueError("Сумма не может быть нулевой")
        return v


class TransactionPatch(BaseModel):
    account_id: int | None = None
    date: dt.date | None = None
    amount: float | None = None
    description: str | None = None
    category_id: int | None = None

    @field_validator("amount")
    @classmethod
    def non_zero(cls, v: float | None) -> float | None:
        if v == 0:
            raise ValueError("Сумма не может быть нулевой")
        return v


class TransactionOut(ORMModel):
    id: int
    account_id: int
    date: dt.date
    amount: float
    description: str
    merchant: str | None
    mcc: str | None
    category_id: int | None
    category_source: str
    source: str
    is_recurring: bool


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
