from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.deps import CurrentUser, DbSession
from app.schemas.analytics import MonthPoint, MonthSummary
from app.services.analytics import dynamics, month_summary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary(
    user: CurrentUser,
    db: DbSession,
    month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
) -> MonthSummary:
    today = date.today()
    year, mon = (int(x) for x in month.split("-")) if month else (today.year, today.month)
    if not 1 <= mon <= 12:
        raise HTTPException(422, "Некорректный месяц")
    return month_summary(db, user, year, mon, today)


@router.get("/dynamics")
def get_dynamics(
    user: CurrentUser, db: DbSession, months: Annotated[int, Query(ge=2, le=24)] = 6
) -> list[MonthPoint]:
    return dynamics(db, user, months, date.today())
