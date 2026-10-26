from datetime import date

from pydantic import BaseModel

from app.schemas.common import ORMModel


class DemoProfile(BaseModel):
    key: str
    title: str
    description: str


class DemoLoginRequest(BaseModel):
    # None — новый пустой пользователь (сценарий онбординга)
    profile: str | None = None


class UserOut(ORMModel):
    id: int
    email: str
    name: str
    profile: str | None
    is_premium: bool
    trial_until: date | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
