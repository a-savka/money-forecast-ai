"""MOCK: авторизация без пароля под демо-профилями.

В реальной версии — регистрация по email/телефону с подтверждением и OAuth (VK ID, Сбер ID).
"""

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import User
from app.schemas.auth import DemoLoginRequest, DemoProfile, TokenResponse, UserOut
from app.security import create_access_token
from app.seed.synthetic import PROFILES
from app.services.demo_data import load_synthetic_profile

router = APIRouter(prefix="/auth", tags=["auth"])

DEMO_NAMES = {
    "young": "Артём",
    "family": "Семья Ивановых",
    "freelancer": "Алина",
    "dropout": "Максим",
}


@router.get("/demo-profiles")
def demo_profiles() -> list[DemoProfile]:
    return [
        DemoProfile(key=p.key, title=p.title, description=p.description) for p in PROFILES.values()
    ]


@router.post("/demo-login")
def demo_login(body: DemoLoginRequest, db: DbSession) -> TokenResponse:
    if body.profile is None:
        user = User(
            email=f"user-{uuid.uuid4().hex[:8]}@moneyforecast.local", name="Новый пользователь"
        )
        db.add(user)
        db.commit()
    else:
        if body.profile not in PROFILES:
            raise HTTPException(404, "Неизвестный демо-профиль")
        email = f"demo-{body.profile}@moneyforecast.local"
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email, name=DEMO_NAMES.get(body.profile, "Демо"), profile=body.profile
            )
            db.add(user)
            db.commit()
            load_synthetic_profile(db, user, body.profile)
    return TokenResponse(
        access_token=create_access_token(user.id), user=UserOut.model_validate(user)
    )


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
