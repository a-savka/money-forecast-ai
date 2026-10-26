from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.deps import CurrentUser, DbSession
from app.forecasting.data import history_from_db
from app.forecasting.engine import month_end, run_forecast
from app.forecasting.registry import DEFAULT_STRATEGY, STRATEGIES
from app.forecasting.schemas import ForecastResult

router = APIRouter(prefix="/forecast", tags=["forecast"])


class StrategyInfo(BaseModel):
    name: str
    title: str
    description: str
    is_default: bool


def horizon_end(as_of: date, horizon: str) -> date:
    if horizon == "week":
        return as_of + timedelta(days=7)
    end = month_end(as_of)
    # В последнюю неделю месяца прогнозируем уже до конца следующего месяца
    return end if (end - as_of).days >= 7 else month_end(end + timedelta(days=1))


@router.get("/strategies")
def strategies() -> list[StrategyInfo]:
    return [
        StrategyInfo(
            name=s.name,
            title=s.title,
            description=s.description,
            is_default=s.name == DEFAULT_STRATEGY,
        )
        for s in STRATEGIES.values()
    ]


@router.get("")
def forecast(
    user: CurrentUser,
    db: DbSession,
    strategy: str = DEFAULT_STRATEGY,
    horizon: Annotated[Literal["week", "month"], Query()] = "month",
) -> ForecastResult:
    if strategy not in STRATEGIES:
        raise HTTPException(404, "Неизвестная стратегия прогноза")
    as_of = date.today()
    history = history_from_db(db, user, as_of)
    if history.txs.empty:
        raise HTTPException(409, "Недостаточно данных для прогноза: добавьте операции")
    return run_forecast(STRATEGIES[strategy], history, horizon_end(as_of, horizon), seed=user.id)
