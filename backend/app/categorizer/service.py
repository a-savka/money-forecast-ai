"""Каскадная категоризация операций.

Порядок: правила пользователя → категория банка → ключевые слова → общая категория банка
(«Переводы», «Пополнения») → MCC → «Прочее».
Ключевые слова идут раньше MCC, потому что MCC бывает слишком общим
(например, доставка еды и фастфуд имеют один код 5814).
"""

import re
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.categorizer.dictionaries import (
    BANK_CATEGORIES,
    EXPENSE_KEYWORDS,
    INCOME_KEYWORDS,
    MCC_CATEGORIES,
)
from app.models import CategoryRule, User
from app.services.categories import category_ids_by_slug


@dataclass(frozen=True)
class CategoryGuess:
    category_id: int
    source: str  # rule | bank | keyword | mcc | default


def normalize(text: str) -> str:
    """Нижний регистр, ё→е не делаем (в словаре есть оба варианта), убираем маски карт и цифры."""
    text = text.lower().strip()
    text = re.sub(r"\*+\d+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def rule_pattern(description: str) -> str:
    """Шаблон для пользовательского правила: описание без чисел и лишних пробелов."""
    return re.sub(r"\s+", " ", re.sub(r"\d+", " ", normalize(description))).strip()


class Categorizer:
    def __init__(self, db: Session, user: User | None = None):
        self.slugs = category_ids_by_slug(db)
        query = select(CategoryRule).order_by(CategoryRule.priority, CategoryRule.id.desc())
        if user is not None:
            query = query.where(
                or_(CategoryRule.user_id == user.id, CategoryRule.user_id.is_(None))
            )
        else:
            query = query.where(CategoryRule.user_id.is_(None))
        self.rules = db.scalars(query).all()

    def _guess(self, slug: str, source: str) -> CategoryGuess:
        return CategoryGuess(self.slugs[slug], source)

    def categorize(
        self,
        description: str,
        amount: float,
        mcc: str | None = None,
        bank_category: str | None = None,
    ) -> CategoryGuess:
        text = normalize(description)
        is_income = amount > 0

        for rule in self.rules:
            if rule.mcc and rule.mcc != mcc:
                continue
            if rule.pattern and rule.pattern not in text:
                continue
            if rule.pattern or rule.mcc:
                return CategoryGuess(rule.category_id, "rule")

        bank_slug = BANK_CATEGORIES.get((bank_category or "").strip().lower())
        if bank_slug and (bank_slug in INCOME_SLUGS) != is_income:
            bank_slug = None
        if bank_slug and bank_slug not in GENERIC_BANK_SLUGS:
            return self._guess(bank_slug, "bank")

        for keyword, slug in INCOME_KEYWORDS if is_income else EXPENSE_KEYWORDS:
            if keyword in text:
                return self._guess(slug, "keyword")

        if bank_slug:
            return self._guess(bank_slug, "bank")

        if not is_income and mcc and mcc in MCC_CATEGORIES:
            return self._guess(MCC_CATEGORIES[mcc], "mcc")

        return self._guess("income_other" if is_income else "other", "default")


INCOME_SLUGS = {"salary", "freelance", "income_other"}
# Слишком общие категории банка — уступают ключевым словам
GENERIC_BANK_SLUGS = {"income_other", "transfers"}
