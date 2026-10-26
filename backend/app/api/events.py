import statistics

from fastapi import APIRouter
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.models import AppEvent
from app.schemas.events import EventIn, EventStats

router = APIRouter(prefix="/events", tags=["events"])

TIME_TO_VALUE_TARGET = 120


@router.post("", status_code=204)
def track(body: EventIn, user: CurrentUser, db: DbSession) -> None:
    db.add(AppEvent(user_id=user.id, name=body.name, props=body.props))
    db.commit()


@router.get("/stats")
def stats(_: CurrentUser, db: DbSession) -> EventStats:
    """Сводка по всем пользователям: сколько событий и time-to-value онбординга."""
    counts = dict(db.execute(select(AppEvent.name, func.count()).group_by(AppEvent.name)).all())
    durations = [
        float(p["seconds"])
        for p in db.scalars(select(AppEvent.props).where(AppEvent.name == "onboarding_done"))
        if isinstance(p, dict) and isinstance(p.get("seconds"), int | float)
    ]
    return EventStats(
        counts=counts,
        onboarding_median_seconds=statistics.median(durations) if durations else None,
        onboarding_under_2_min_share=(
            sum(d <= TIME_TO_VALUE_TARGET for d in durations) / len(durations)
            if durations
            else None
        ),
    )
