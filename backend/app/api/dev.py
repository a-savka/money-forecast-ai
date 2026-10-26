"""Служебные эндпоинты для демо: перезаливка синтетических данных."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.deps import CurrentUser, DbSession
from app.seed.synthetic import PROFILES
from app.services.demo_data import clear_user_data, load_synthetic_profile

router = APIRouter(prefix="/dev", tags=["dev"])


class SeedRequest(BaseModel):
    profile: str
    months: int = 12
    seed: int = 42


@router.post("/seed", status_code=204)
def seed(body: SeedRequest, user: CurrentUser, db: DbSession) -> None:
    if body.profile not in PROFILES:
        raise HTTPException(404, "Неизвестный демо-профиль")
    clear_user_data(db, user)
    load_synthetic_profile(db, user, body.profile, months=body.months, seed=body.seed)
    user.profile = body.profile
    db.commit()


@router.post("/reset", status_code=204)
def reset(user: CurrentUser, db: DbSession) -> None:
    clear_user_data(db, user)
    db.commit()
