"""MOCK-эндпоинты функций, которые в MVP имитируются (подписка, семья, лимиты, push)."""

from datetime import date

from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, DbSession
from app.models import User
from app.schemas.subscription import SubscriptionAction, SubscriptionOut
from app.services import subscription as sub

router = APIRouter(prefix="/mock", tags=["mock"])


def subscription_out(user: User) -> SubscriptionOut:
    today = date.today()
    current = sub.plan(user, today)
    left = (user.trial_until - today).days + 1 if current == "trial" and user.trial_until else 0
    return SubscriptionOut(
        plan=current,
        trial_until=user.trial_until,
        trial_days_left=left,
        can_start_trial=user.trial_until is None and not user.is_premium,
        price_month=sub.PRICE_MONTH_RUB,
        price_year=sub.PRICE_YEAR_RUB,
    )


@router.get("/subscription")
def get_subscription(user: CurrentUser) -> SubscriptionOut:
    return subscription_out(user)


@router.post("/subscription")
def change_subscription(
    body: SubscriptionAction, user: CurrentUser, db: DbSession
) -> SubscriptionOut:
    try:
        if body.action == "start_trial":
            sub.start_trial(user)
        elif body.action == "upgrade":
            sub.upgrade(user)
        else:
            sub.cancel(user)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return subscription_out(user)
