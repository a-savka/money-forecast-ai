"""MOCK-эндпоинты функций, которые в MVP имитируются (подписка, семья, лимиты, push)."""

from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.models import Budget, Category, Family, User
from app.schemas.budgets import BudgetIn, BudgetOut, BudgetSuggestion
from app.schemas.family import FamilyCreate, FamilyJoin, FamilyMemberOut, FamilyOut
from app.schemas.subscription import SubscriptionAction, SubscriptionOut
from app.services import budgets as bud
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


@router.get("/budgets")
def list_budgets(user: CurrentUser, db: DbSession) -> list[BudgetOut]:
    return [BudgetOut(**vars(s)) for s in bud.budget_statuses(db, user, date.today())]


@router.get("/budgets/suggest")
def suggest_budgets(user: CurrentUser, db: DbSession) -> list[BudgetSuggestion]:
    limits = bud.suggest_limits(db, user, date.today())
    return [BudgetSuggestion(category_id=c, limit=v) for c, v in limits.items()]


@router.put("/budgets")
def put_budget(body: BudgetIn, user: CurrentUser, db: DbSession) -> list[BudgetOut]:
    category = db.get(Category, body.category_id)
    if category is None or category.kind != "expense":
        raise HTTPException(422, "Лимит можно задать только для категории расходов")
    exists = db.scalar(
        select(Budget).where(Budget.user_id == user.id, Budget.category_id == body.category_id)
    )
    count = db.scalar(select(func.count()).where(Budget.user_id == user.id)) or 0
    if exists is None and count >= bud.FREE_LIMIT and not sub.has_premium(user):
        raise HTTPException(402, "В Free доступен один лимит — больше в Premium")
    bud.upsert_budget(db, user, body.category_id, body.limit)
    return list_budgets(user, db)


@router.delete("/budgets/{budget_id}")
def delete_budget(budget_id: int, user: CurrentUser, db: DbSession) -> list[BudgetOut]:
    budget = db.get(Budget, budget_id)
    if budget is None or budget.user_id != user.id:
        raise HTTPException(404, "Лимит не найден")
    db.delete(budget)
    db.commit()
    return list_budgets(user, db)
