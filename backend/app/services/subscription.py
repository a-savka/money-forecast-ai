"""MOCK: подписка Free / Premium без платежей.

В реальной версии статус приходит из платёжного провайдера (ЮKassa / RuStore Billing)
через вебхук; здесь кнопки «Попробовать» и «Оформить» просто меняют флаги пользователя.
"""

from datetime import date, timedelta

from app.models import User

TRIAL_DAYS = 7
PRICE_MONTH_RUB = 299
PRICE_YEAR_RUB = 2490


def plan(user: User, today: date | None = None) -> str:
    today = today or date.today()
    if user.is_premium:
        return "premium"
    if user.trial_until and user.trial_until >= today:
        return "trial"
    return "free"


def has_premium(user: User, today: date | None = None) -> bool:
    return plan(user, today) != "free"


def start_trial(user: User, today: date | None = None) -> None:
    today = today or date.today()
    if user.trial_until is not None:
        raise ValueError("Пробный период уже использован")
    user.trial_until = today + timedelta(days=TRIAL_DAYS - 1)


def upgrade(user: User) -> None:
    user.is_premium = True


def cancel(user: User, today: date | None = None) -> None:
    today = today or date.today()
    user.is_premium = False
    if user.trial_until and user.trial_until >= today:
        user.trial_until = today - timedelta(days=1)
