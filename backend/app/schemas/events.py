from typing import Any, Literal

from pydantic import BaseModel, Field

EventName = Literal[
    "onboarding_started",
    "onboarding_done",
    "forecast_viewed",
    "paywall_shown",
    "trial_started",
    "subscription_upgraded",
]


class EventIn(BaseModel):
    name: EventName
    props: dict[str, Any] = Field(default_factory=dict)


class EventStats(BaseModel):
    counts: dict[str, int]
    onboarding_median_seconds: float | None
    onboarding_under_2_min_share: float | None
