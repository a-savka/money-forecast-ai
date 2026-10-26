from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.models import Account, Category, Transaction, User
from app.schemas.finance import (
    AccountIn,
    AccountOut,
    CategoryOut,
    TransactionIn,
    TransactionOut,
    TransactionPage,
    TransactionPatch,
)
from app.services.accounts import account_balances, get_or_create_default_account

router = APIRouter(tags=["finance"])


def _money(x: float) -> Decimal:
    return Decimal(str(round(x, 2)))


def _own_account(db: DbSession, user: User, account_id: int) -> Account:
    acc = db.get(Account, account_id)
    if acc is None or acc.user_id != user.id:
        raise HTTPException(404, "Счёт не найден")
    return acc


def _own_tx(db: DbSession, user: User, tx_id: int) -> Transaction:
    tx = db.get(Transaction, tx_id)
    if tx is None or tx.user_id != user.id:
        raise HTTPException(404, "Операция не найдена")
    return tx


def _check_category(db: DbSession, category_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(422, "Категория не найдена")


@router.get("/categories")
def list_categories(db: DbSession) -> list[CategoryOut]:
    cats = db.scalars(select(Category).order_by(Category.id)).all()
    return [CategoryOut.model_validate(c) for c in cats]


@router.get("/accounts")
def list_accounts(user: CurrentUser, db: DbSession) -> list[AccountOut]:
    balances = account_balances(db, user)
    accounts = db.scalars(select(Account).where(Account.user_id == user.id).order_by(Account.id))
    return [
        AccountOut.model_validate(a).model_copy(update={"balance": float(balances[a.id])})
        for a in accounts
    ]


@router.post("/accounts", status_code=201)
def create_account(body: AccountIn, user: CurrentUser, db: DbSession) -> AccountOut:
    acc = Account(
        user_id=user.id,
        name=body.name,
        bank_name=body.bank_name,
        type=body.type,
        balance_initial=_money(body.balance_initial),
    )
    db.add(acc)
    db.commit()
    return AccountOut.model_validate(acc).model_copy(update={"balance": body.balance_initial})


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: int, user: CurrentUser, db: DbSession) -> None:
    db.delete(_own_account(db, user, account_id))
    db.commit()


@router.get("/transactions")
def list_transactions(
    user: CurrentUser,
    db: DbSession,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    category_id: int | None = None,
    account_id: int | None = None,
    kind: Literal["expense", "income"] | None = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionPage:
    conds = [Transaction.user_id == user.id]
    if date_from:
        conds.append(Transaction.date >= date_from)
    if date_to:
        conds.append(Transaction.date <= date_to)
    if category_id:
        conds.append(Transaction.category_id == category_id)
    if account_id:
        conds.append(Transaction.account_id == account_id)
    if kind == "expense":
        conds.append(Transaction.amount < 0)
    elif kind == "income":
        conds.append(Transaction.amount > 0)
    if q:
        conds.append(Transaction.description.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(Transaction).where(*conds)) or 0
    rows = db.scalars(
        select(Transaction)
        .where(*conds)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return TransactionPage(items=[TransactionOut.model_validate(t) for t in rows], total=total)


@router.post("/transactions", status_code=201)
def create_transaction(body: TransactionIn, user: CurrentUser, db: DbSession) -> TransactionOut:
    if body.account_id is not None:
        acc = _own_account(db, user, body.account_id)
    else:
        acc = get_or_create_default_account(db, user)
    _check_category(db, body.category_id)
    tx = Transaction(
        user_id=user.id,
        account_id=acc.id,
        date=body.date,
        amount=_money(body.amount),
        description=body.description,
        mcc=body.mcc,
        category_id=body.category_id,
        category_source="user",
        source="manual",
    )
    db.add(tx)
    db.commit()
    return TransactionOut.model_validate(tx)


@router.patch("/transactions/{tx_id}")
def update_transaction(
    tx_id: int, body: TransactionPatch, user: CurrentUser, db: DbSession
) -> TransactionOut:
    tx = _own_tx(db, user, tx_id)
    data = body.model_dump(exclude_unset=True)
    if "account_id" in data and data["account_id"] is not None:
        _own_account(db, user, data["account_id"])
    if "category_id" in data:
        _check_category(db, data["category_id"])
        tx.category_source = "user"
    if "amount" in data and data["amount"] is not None:
        data["amount"] = _money(data["amount"])
    for key, value in data.items():
        if value is not None or key == "category_id":
            setattr(tx, key, value)
    db.commit()
    return TransactionOut.model_validate(tx)


@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, user: CurrentUser, db: DbSession) -> None:
    db.delete(_own_tx(db, user, tx_id))
    db.commit()
