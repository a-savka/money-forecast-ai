"""Лимиты по категориям: сколько потрачено, темп и когда лимит закончится.

Темп трат — смесь текущего месяца и истории за 90 дней: в начале месяца одна покупка
не должна давать прогноз «лимит кончится завтра».
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Budget, Category, Transaction, User

FREE_LIMIT = 1  # MOCK freemium: в Free — один лимит, в Premium — без ограничений
HISTORY_DAYS = 90
PRIOR_DAYS = 7  # «вес» истории в днях при смешивании с текущим месяцем
WARNING_SHARE = 0.85


@dataclass
class BudgetStatus:
    id: int
    category_id: int
    limit: float
    spent: float
    remaining: float
    projected: float  # ожидаемые траты к концу месяца
    daily_pace: float
    days_left_in_month: int
    exhausted_in_days: int | None  # через сколько дней закончится лимит при текущем темпе
    status: str  # ok | warning | over


def spend_by_category(db: Session, user: User, start: date, end: date) -> dict[int, float]:
    rows = db.execute(
        select(Transaction.category_id, func.sum(-Transaction.amount))
        .where(
            Transaction.user_id == user.id,
            Transaction.amount < 0,
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .group_by(Transaction.category_id)
    ).all()
    return {cid: float(total) for cid, total in rows if cid is not None}


def budget_statuses(db: Session, user: User, today: date) -> list[BudgetStatus]:
    budgets = db.scalars(select(Budget).where(Budget.user_id == user.id)).all()
    if not budgets:
        return []
    month_start = today.replace(day=1)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    elapsed = today.day
    left = days_in_month - elapsed
    current = spend_by_category(db, user, month_start, today)
    history = spend_by_category(
        db, user, month_start - timedelta(days=HISTORY_DAYS), month_start - timedelta(days=1)
    )

    out = []
    for b in budgets:
        limit = float(b.limit_amount)
        spent = current.get(b.category_id, 0.0)
        hist_daily = history.get(b.category_id, 0.0) / HISTORY_DAYS
        pace = (spent + hist_daily * PRIOR_DAYS) / (elapsed + PRIOR_DAYS)
        projected = spent + pace * left
        remaining = limit - spent
        if remaining <= 0:
            exhausted, status = 0, "over"
        else:
            exhausted = int(remaining // pace) if pace > 0 else None
            in_month = exhausted is not None and exhausted < left
            status = "warning" if in_month or spent >= limit * WARNING_SHARE else "ok"
        out.append(
            BudgetStatus(
                id=b.id,
                category_id=b.category_id,
                limit=limit,
                spent=round(spent, 2),
                remaining=round(remaining, 2),
                projected=round(projected, 2),
                daily_pace=round(pace, 2),
                days_left_in_month=left,
                exhausted_in_days=exhausted,
                status=status,
            )
        )
    order = {"over": 0, "warning": 1, "ok": 2}
    out.sort(key=lambda s: (order[s.status], -s.spent / max(s.limit, 1)))
    return out


def suggest_limits(db: Session, user: User, today: date) -> dict[int, float]:
    """Средние траты в месяц за 3 месяца по «необязательным» категориям, округлённые вверх."""
    month_start = today.replace(day=1)
    hist = spend_by_category(
        db, user, month_start - timedelta(days=HISTORY_DAYS), month_start - timedelta(days=1)
    )
    discretionary = set(
        db.scalars(select(Category.id).where(Category.is_discretionary.is_(True))).all()
    )
    out = {}
    for cid, total in sorted(hist.items(), key=lambda p: -p[1]):
        if cid in discretionary and total > 0:
            monthly = total / (HISTORY_DAYS / 30)
            out[cid] = float(-(-monthly // 500) * 500)  # вверх до 500 ₽
    return out


def upsert_budget(db: Session, user: User, category_id: int, limit: Decimal) -> Budget:
    budget = db.scalar(
        select(Budget).where(Budget.user_id == user.id, Budget.category_id == category_id)
    )
    if budget is None:
        budget = Budget(user_id=user.id, category_id=category_id, limit_amount=limit)
        db.add(budget)
    else:
        budget.limit_amount = limit
    db.commit()
    return budget
