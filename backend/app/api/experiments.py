from datetime import date
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.forecasting.backtest import Dataset, run_backtest
from app.forecasting.data import history_from_db, history_from_synthetic
from app.forecasting.registry import STRATEGIES
from app.models import BacktestRun, Transaction
from app.schemas.experiments import BacktestRequest, BacktestRunOut
from app.seed.synthetic import PROFILES, generate_profile

router = APIRouter(prefix="/experiments", tags=["experiments"])


@lru_cache(maxsize=4)
def demo_datasets(end: date) -> tuple[Dataset, ...]:
    """Четыре синтетических профиля — общий стенд для сравнения гипотез."""
    return tuple(
        Dataset(key, history_from_synthetic(generate_profile(key, end=end), end))
        for key in PROFILES
    )


@router.post("/backtest")
def backtest(body: BacktestRequest, user: CurrentUser, db: DbSession) -> list[BacktestRunOut]:
    names = body.strategies or list(STRATEGIES)
    unknown = set(names) - set(STRATEGIES)
    if unknown:
        raise HTTPException(404, f"Неизвестные стратегии: {', '.join(sorted(unknown))}")

    if body.dataset == "demo":
        datasets = list(demo_datasets(date.today()))
    else:
        last = db.scalar(select(func.max(Transaction.date)).where(Transaction.user_id == user.id))
        if last is None:
            raise HTTPException(409, "Нет операций для бэктеста — загрузите выписку")
        datasets = [Dataset("me", history_from_db(db, user, last))]

    reports = run_backtest({n: STRATEGIES[n] for n in names}, datasets, months=body.months)
    if not reports[0].cases:
        raise HTTPException(409, "Мало истории: для бэктеста нужно 4+ месяца операций")

    runs = [
        BacktestRun(
            user_id=user.id,
            strategy=r.strategy,
            dataset=body.dataset,
            params={"months": body.months, "datasets": [d.name for d in datasets]},
            metrics=r.metrics,
            cases=r.cases_json(),
            duration_ms=r.duration_ms,
            llm_cost=float(r.metrics.get("llm_cost_rub") or 0),
        )
        for r in reports
    ]
    db.add_all(runs)
    db.commit()
    return [BacktestRunOut.model_validate(r) for r in runs]


@router.get("")
def experiments(user: CurrentUser, db: DbSession, limit: int = 20) -> list[BacktestRunOut]:
    runs = db.scalars(
        select(BacktestRun)
        .where(BacktestRun.user_id == user.id)
        .order_by(BacktestRun.created_at.desc(), BacktestRun.id.desc())
        .limit(limit)
    ).all()
    return [BacktestRunOut.model_validate(r) for r in runs]
