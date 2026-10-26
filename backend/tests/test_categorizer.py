from datetime import date

import pytest

from app.categorizer.service import Categorizer, rule_pattern
from app.models import CategoryRule, User
from app.seed.synthetic import PROFILES, generate_profile
from app.services.categories import category_ids_by_slug


@pytest.fixture
def cat(db):
    return Categorizer(db)


@pytest.fixture
def slugs(db):
    return {v: k for k, v in category_ids_by_slug(db).items()}


@pytest.mark.parametrize(
    ("description", "amount", "mcc", "expected"),
    [
        ("ПЯТЁРОЧКА 1234 МОСКВА", -500, "5411", "products"),
        ("ЯНДЕКС ЕДА", -900, "5814", "delivery"),
        ("ВКУСНО И ТОЧКА", -400, "5814", "cafe"),
        ("Неизвестный магазин", -400, "5651", "clothes"),
        ("Зарплата ООО Ромашка", 50000, None, "salary"),
        ("Оплата по договору ИП Иванов", 20000, None, "freelance"),
        ("Что-то странное", -100, None, "other"),
        ("Что-то странное", 100, None, "income_other"),
        ("ОСАГО/КАСКО рассрочка", -3200, "6300", "transport"),
    ],
)
def test_cascade(cat, slugs, description, amount, mcc, expected):
    assert slugs[cat.categorize(description, amount, mcc).category_id] == expected


def test_bank_category_has_priority_over_keywords(cat, slugs):
    guess = cat.categorize("ООО ВЕКТОР", -1000, None, bank_category="Аптеки")
    assert slugs[guess.category_id] == "health"
    assert guess.source == "bank"


def test_user_rule_wins(db, slugs):
    user = User(email="r@x.ru", name="R")
    db.add(user)
    db.flush()
    ids = category_ids_by_slug(db)
    db.add(
        CategoryRule(
            user_id=user.id, pattern=rule_pattern("ПЯТЁРОЧКА 1234"), category_id=ids["cafe"]
        )
    )
    db.commit()
    guess = Categorizer(db, user).categorize("ПЯТЁРОЧКА 9999", -500, "5411")
    assert (slugs[guess.category_id], guess.source) == ("cafe", "rule")
    # Чужие правила не применяются
    assert slugs[Categorizer(db).categorize("ПЯТЁРОЧКА", -500, "5411").category_id] == "products"


@pytest.mark.parametrize("key", list(PROFILES))
def test_accuracy_on_synthetic_profiles(cat, slugs, key):
    """Критерий приёмки W2-4: ≥ 85% операций категоризируются верно без подсказок банка."""
    txs = generate_profile(key, end=date(2026, 10, 26)).transactions
    correct = sum(
        slugs[cat.categorize(t.description, float(t.amount), t.mcc).category_id] == t.category
        for t in txs
    )
    assert correct / len(txs) >= 0.85
