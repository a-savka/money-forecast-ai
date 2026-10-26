from typing import Literal

from pydantic import BaseModel, Field


class FamilyMemberOut(BaseModel):
    user_id: int
    name: str
    role: Literal["owner", "member"]
    balance: float
    month_expense: float
    is_me: bool


class FamilyOut(BaseModel):
    id: int
    name: str
    invite_code: str
    my_role: Literal["owner", "member"]
    members: list[FamilyMemberOut]
    total_balance: float
    total_month_expense: float


class FamilyCreate(BaseModel):
    name: str = Field("Моя семья", max_length=64)


class FamilyJoin(BaseModel):
    code: str = Field(min_length=4, max_length=12)
