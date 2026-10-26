"""Алерты для уведомлений: риск кассового разрыва, лимиты, крупные платежи завтра.

MOCK: в реальной версии алерты считает фоновая задача и отправляет push через FCM/RuStore;
в MVP клиент сам опрашивает /mock/notifications и показывает локальное уведомление.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.forecasting.schemas import ForecastResult
from app.models import Category, User
from app.services.budgets import budget_statuses

BIG_PAYMENT_RUB = 3000


@dataclass
class Alert:
    id: str  # стабильный в пределах дня — клиент не показывает одно и то же дважды
    kind: str  # cash_gap | budget | payment | test
    severity: str  # info | warning | critical
    title: str
    body: str
    link: str


def _rub(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ") + " ₽"


def _date(d: date) -> str:
    months = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря"
    return f"{d.day} {months.split()[d.month - 1]}"


def build_alerts(
    db: Session, user: User, forecast: ForecastResult | None, today: date
) -> list[Alert]:
    alerts: list[Alert] = []
    if forecast and forecast.cash_gap.risk in ("medium", "high"):
        gap = forecast.cash_gap
        when = f" около {_date(gap.first_negative_date)}" if gap.first_negative_date else ""
        alerts.append(
            Alert(
                id=f"gap-{gap.risk}-{today.isoformat()}",
                kind="cash_gap",
                severity="critical" if gap.risk == "high" else "warning",
                title="Риск кассового разрыва" + (" — высокий" if gap.risk == "high" else ""),
                body=f"Деньги могут закончиться{when} "
                f"(вероятность {round(gap.probability * 100)}%). "
                "Посмотрите советы, как этого избежать.",
                link="/recommendations",
            )
        )

    names = {c.id: c.name for c in db.query(Category).all()}
    for b in budget_statuses(db, user, today):
        if b.status == "ok":
            continue
        name = names.get(b.category_id, "категории")
        if b.status == "over":
            body = f"Лимит «{name}» превышен на {_rub(-b.remaining)}."
        else:
            body = (
                f"При текущем темпе лимит «{name}» закончится через {b.exhausted_in_days} дн."
                if b.exhausted_in_days is not None
                else f"Потрачено {_rub(b.spent)} из {_rub(b.limit)}."
            )
        alerts.append(
            Alert(
                id=f"budget-{b.id}-{b.status}-{today.isoformat()}",
                kind="budget",
                severity="critical" if b.status == "over" else "warning",
                title="Лимит по категории",
                body=body,
                link="/budgets",
            )
        )

    if forecast:
        tomorrow = today + timedelta(days=1)
        for p in forecast.upcoming:
            if p.date == tomorrow and p.amount <= -BIG_PAYMENT_RUB:
                alerts.append(
                    Alert(
                        id=f"payment-{p.name}-{p.date.isoformat()}",
                        kind="payment",
                        severity="info",
                        title="Завтра платёж",
                        body=f"{p.name}: {_rub(-p.amount)}. Проверьте, хватает ли денег на счёте.",
                        link="/forecast",
                    )
                )
    return alerts


def sample_alert(today: date) -> Alert:
    return Alert(
        id=f"test-{today.isoformat()}",
        kind="test",
        severity="info",
        title="MoneyForecast",
        body="Тестовое уведомление: так мы предупредим о риске уйти в минус.",
        link="/",
    )
