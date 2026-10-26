import calendar
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Transaction, User
from app.schemas.analytics import CategoryAmount, MonthPoint, MonthSummary


def month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def _sums_by_category(db: Session, user: User, start: date, end: date) -> dict[int, tuple]:
    """{category_id: (сумма, количество)} без переводов между своими счетами."""
    rows = db.execute(
        select(Transaction.category_id, func.sum(Transaction.amount), func.count())
        .join(Category, Category.id == Transaction.category_id, isouter=True)
        .where(
            Transaction.user_id == user.id,
            Transaction.date >= start,
            Transaction.date <= end,
            func.coalesce(Category.kind, "expense") != "transfer",
        )
        .group_by(Transaction.category_id)
    ).all()
    return {cid: (float(total), n) for cid, total, n in rows}


def month_summary(db: Session, user: User, year: int, month: int, today: date) -> MonthSummary:
    start, end = month_bounds(year, month)
    days_in_month = end.day
    is_current = (year, month) == (today.year, today.month)
    days_elapsed = today.day if is_current else days_in_month

    py, pm = shift_month(year, month, -1)
    prev_start, prev_end = month_bounds(py, pm)
    # Для текущего месяца сравниваем с тем же числом прошлого месяца
    prev_cut = prev_end if not is_current else prev_start.replace(day=min(today.day, prev_end.day))

    cur = _sums_by_category(db, user, start, end)
    prev = _sums_by_category(db, user, prev_start, prev_cut)

    expense_by_cat = {cid: -s for cid, (s, _) in cur.items() if s < 0 and cid is not None}
    total_expense = sum(expense_by_cat.values())
    income = sum(s for s, _ in cur.values() if s > 0)
    prev_expense = sum(-s for s, _ in prev.values() if s < 0)

    by_category = sorted(
        (
            CategoryAmount(
                category_id=cid,
                amount=round(amount, 2),
                count=cur[cid][1],
                share=amount / total_expense if total_expense else 0,
                prev_amount=round(max(0.0, -prev.get(cid, (0, 0))[0]), 2),
            )
            for cid, amount in expense_by_cat.items()
        ),
        key=lambda c: c.amount,
        reverse=True,
    )
    return MonthSummary(
        month=f"{year:04d}-{month:02d}",
        income=round(income, 2),
        expense=round(total_expense, 2),
        net=round(income - total_expense, 2),
        prev_expense=round(prev_expense, 2),
        days_elapsed=days_elapsed,
        days_in_month=days_in_month,
        by_category=by_category,
    )


def dynamics(db: Session, user: User, months: int, today: date) -> list[MonthPoint]:
    first_y, first_m = shift_month(today.year, today.month, -(months - 1))
    start = date(first_y, first_m, 1)
    rows = db.execute(
        select(Transaction.date, Transaction.amount)
        .join(Category, Category.id == Transaction.category_id, isouter=True)
        .where(
            Transaction.user_id == user.id,
            Transaction.date >= start,
            func.coalesce(Category.kind, "expense") != "transfer",
        )
    ).all()
    income: dict[str, float] = defaultdict(float)
    expense: dict[str, float] = defaultdict(float)
    for d, amount in rows:
        key = f"{d.year:04d}-{d.month:02d}"
        if amount > 0:
            income[key] += float(amount)
        else:
            expense[key] -= float(amount)
    points = []
    for i in range(months):
        y, m = shift_month(first_y, first_m, i)
        key = f"{y:04d}-{m:02d}"
        points.append(MonthPoint(month=key, income=round(income[key]), expense=round(expense[key])))
    return points
