from typing import Literal

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: str
    kind: Literal["cash_gap", "budget", "payment", "test"]
    severity: Literal["info", "warning", "critical"]
    title: str
    body: str
    link: str
