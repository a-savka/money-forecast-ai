from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import Account, Category, Transaction, User
from app.services.categories import SYSTEM_CATEGORIES, ensure_system_categories


def test_system_categories_seeded_idempotently(db):
    ensure_system_categories(db)
    cats = db.scalars(select(Category)).all()
    assert len(cats) == len(SYSTEM_CATEGORIES)


def test_transaction_roundtrip(db):
    user = User(email="a@b.c", name="Тест")
    db.add(user)
    db.flush()
    acc = Account(user_id=user.id, name="Карта", balance_initial=Decimal("1000"))
    db.add(acc)
    db.flush()
    products = db.scalar(select(Category).where(Category.slug == "products"))
    db.add(
        Transaction(
            user_id=user.id,
            account_id=acc.id,
            date=date(2026, 10, 1),
            amount=Decimal("-250.50"),
            description="Пятёрочка",
            category_id=products.id,
        )
    )
    db.commit()
    tx = db.scalar(select(Transaction))
    assert tx.amount == Decimal("-250.50")
    assert tx.category.slug == "products"
