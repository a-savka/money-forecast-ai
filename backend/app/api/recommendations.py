from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.forecast import horizon_end
from app.deps import CurrentUser, DbSession
from app.forecasting.data import history_from_db
from app.forecasting.engine import run_forecast
from app.forecasting.recommendations import (
    Recommendation,
    llm_recommendations,
    rule_recommendations,
)
from app.forecasting.registry import DEFAULT_STRATEGY, STRATEGIES

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendationsOut(BaseModel):
    items: list[Recommendation]
    mode: str
    info: dict = {}


@router.get("")
def recommendations(
    user: CurrentUser,
    db: DbSession,
    strategy: str = DEFAULT_STRATEGY,
    mode: Literal["rules", "llm"] = "rules",
) -> RecommendationsOut:
    if strategy not in STRATEGIES:
        raise HTTPException(404, "Неизвестная стратегия прогноза")
    as_of = date.today()
    history = history_from_db(db, user, as_of)
    if history.txs.empty:
        return RecommendationsOut(items=[], mode=mode)
    forecast = run_forecast(
        STRATEGIES[strategy], history, horizon_end(as_of, "month"), seed=user.id
    )
    recs = rule_recommendations(forecast, history)
    info: dict = {}
    if mode == "llm":
        recs, info = llm_recommendations(recs, forecast)
    return RecommendationsOut(items=recs, mode=mode, info=info)
