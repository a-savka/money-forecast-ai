from datetime import date

import pytest
from sqlalchemy import func, select

from app.models import Transaction, User
from app.seed.synthetic import PROFILES, generate_profile, random_profile_spec
from app.services.categories import SYSTEM_CATEGORIES
from app.services.demo_data import load_synthetic_profile

END = date(2026, 10, 26)
SLUGS = {c.slug for c in SYSTEM_CATEGORIES}


@pytest.mark.parametrize("key", list(PROFILES))
def test_profile_is_deterministic_and_valid(key):
    a = generate_profile(key, end=END)
    b = generate_profile(key, end=END)
    assert a.transactions == b.transactions
    assert a.start == date(2025, 11, 1)
    assert all(a.start <= t.date <= END for t in a.transactions)
    assert {t.category for t in a.transactions} <= SLUGS
    assert len(a.transactions) > 300


@pytest.mark.parametrize("key", list(PROFILES))
def test_spending_close_to_income(key):
    p = generate_profile(key, end=END)
    real = [t for t in p.transactions if t.category != "savings"]
    income = sum(t.amount for t in real if t.amount > 0)
    expense = -sum(t.amount for t in real if t.amount < 0)
    assert 0.75 < expense / income < 1.25


def test_random_profiles_differ():
    a = generate_profile(random_profile_spec(1), end=END)
    b = generate_profile(random_profile_spec(2), end=END)
    assert a.transactions != b.transactions


def test_load_profile_into_db(db):
    user = User(email="demo@x.ru", name="Демо")
    db.add(user)
    db.commit()
    accounts = load_synthetic_profile(db, user, "young", end=END)
    assert len(accounts) == 2
    count = db.scalar(select(func.count()).select_from(Transaction))
    assert count == len(generate_profile("young", end=END).transactions)
