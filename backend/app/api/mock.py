"""MOCK-эндпоинты функций, которые в MVP имитируются (подписка, семья, лимиты, push)."""

from datetime import date

from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, DbSession
from app.models import Family, User
from app.schemas.family import FamilyCreate, FamilyJoin, FamilyMemberOut, FamilyOut
from app.schemas.subscription import SubscriptionAction, SubscriptionOut
from app.services import family as fam
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


def family_out(db: DbSession, user: User) -> FamilyOut | None:
    m = fam.membership(db, user)
    if m is None:
        return None
    family = db.get(Family, m.family_id)
    assert family is not None
    members = fam.members_summary(db, family.id, user, date.today())
    return FamilyOut(
        id=family.id,
        name=family.name,
        invite_code=family.invite_code,
        my_role=m.role,
        members=[FamilyMemberOut(**vars(x)) for x in members],
        total_balance=round(sum(x.balance for x in members), 2),
        total_month_expense=round(sum(x.month_expense for x in members), 2),
    )


@router.get("/family")
def get_family(user: CurrentUser, db: DbSession) -> FamilyOut | None:
    return family_out(db, user)


@router.post("/family")
def create_family(body: FamilyCreate, user: CurrentUser, db: DbSession) -> FamilyOut | None:
    if not sub.has_premium(user):
        raise HTTPException(402, "Создание семьи доступно в Premium")
    try:
        fam.create_family(db, user, body.name)
    except fam.FamilyError as exc:
        raise HTTPException(409, str(exc)) from exc
    return family_out(db, user)


@router.post("/family/join")
def join_family(body: FamilyJoin, user: CurrentUser, db: DbSession) -> FamilyOut | None:
    try:
        fam.join_family(db, user, body.code)
    except fam.FamilyError as exc:
        raise HTTPException(409, str(exc)) from exc
    return family_out(db, user)


@router.post("/family/demo-member")
def add_demo_member(user: CurrentUser, db: DbSession) -> FamilyOut | None:
    try:
        fam.add_demo_member(db, user)
    except fam.FamilyError as exc:
        raise HTTPException(409, str(exc)) from exc
    return family_out(db, user)


@router.post("/family/leave")
def leave_family(user: CurrentUser, db: DbSession) -> FamilyOut | None:
    fam.leave_family(db, user)
    return None
