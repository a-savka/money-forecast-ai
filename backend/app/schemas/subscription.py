import datetime as dt
from typing import Literal

from pydantic import BaseModel


class SubscriptionOut(BaseModel):
    plan: Literal["free", "trial", "premium"]
    trial_until: dt.date | None
    trial_days_left: int
    can_start_trial: bool
    price_month: int
    price_year: int


class SubscriptionAction(BaseModel):
    action: Literal["start_trial", "upgrade", "cancel"]
