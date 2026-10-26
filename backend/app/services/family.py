"""MOCK: семейный режим — общая картина по балансам и тратам участников.

В реальной версии: приглашение по ссылке/SMS, раздельные права на счета,
общие цели и лимиты. Здесь — код-приглашение и сводка «только чтение».
"""

import secrets
from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Family, FamilyMember, User
from app.seed.synthetic import PROFILES
from app.services.accounts import account_balances
from app.services.analytics import month_summary
from app.services.demo_data import get_or_create_demo_user

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # без похожих символов 0/O, 1/I


class FamilyError(ValueError):
    pass


@dataclass
class MemberSummary:
    user_id: int
    name: str
    role: str
    balance: float
    month_expense: float
    is_me: bool


def membership(db: Session, user: User) -> FamilyMember | None:
    return db.scalar(select(FamilyMember).where(FamilyMember.user_id == user.id))


def _new_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if not db.scalar(select(Family).where(Family.invite_code == code)):
            return code


def create_family(db: Session, user: User, name: str) -> Family:
    if membership(db, user):
        raise FamilyError("Вы уже состоите в семье")
    family = Family(name=name.strip() or "Моя семья", invite_code=_new_code(db))
    db.add(family)
    db.flush()
    db.add(FamilyMember(family_id=family.id, user_id=user.id, role="owner"))
    db.commit()
    return family


def join_family(db: Session, user: User, code: str) -> Family:
    if membership(db, user):
        raise FamilyError("Вы уже состоите в семье")
    family = db.scalar(select(Family).where(Family.invite_code == code.strip().upper()))
    if family is None:
        raise FamilyError("Семья с таким кодом не найдена")
    db.add(FamilyMember(family_id=family.id, user_id=user.id, role="member"))
    db.commit()
    return family


def leave_family(db: Session, user: User) -> None:
    m = membership(db, user)
    if m is None:
        return
    if m.role == "owner":
        # Владелец распускает семью целиком
        db.execute(delete(FamilyMember).where(FamilyMember.family_id == m.family_id))
        db.execute(delete(Family).where(Family.id == m.family_id))
    else:
        db.delete(m)
    db.commit()


def add_demo_member(db: Session, user: User) -> User:
    """MOCK: «пригласить» другого демо-пользователя, чтобы показать семейную сводку."""
    m = membership(db, user)
    if m is None:
        raise FamilyError("Сначала создайте семью")
    for key in PROFILES:
        if key == user.profile:
            continue
        partner = get_or_create_demo_user(db, key)
        if membership(db, partner) is None:
            db.add(FamilyMember(family_id=m.family_id, user_id=partner.id, role="member"))
            db.commit()
            return partner
    raise FamilyError("Все демо-пользователи уже в семьях")


def members_summary(db: Session, family_id: int, me: User, today: date) -> list[MemberSummary]:
    rows = db.execute(
        select(FamilyMember, User)
        .join(User, User.id == FamilyMember.user_id)
        .where(FamilyMember.family_id == family_id)
        .order_by(FamilyMember.role.desc(), FamilyMember.id)
    ).all()
    out = []
    for member, user in rows:
        summary = month_summary(db, user, today.year, today.month, today)
        out.append(
            MemberSummary(
                user_id=user.id,
                name=user.name,
                role=member.role,
                balance=round(float(sum(account_balances(db, user).values())), 2),
                month_expense=summary.expense,
                is_me=user.id == me.id,
            )
        )
    return out
