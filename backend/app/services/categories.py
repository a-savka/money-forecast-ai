from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category


@dataclass(frozen=True)
class SystemCategory:
    slug: str
    name: str
    kind: str
    icon: str
    color: str
    is_discretionary: bool = False


SYSTEM_CATEGORIES: list[SystemCategory] = [
    SystemCategory("products", "Продукты", "expense", "shopping-cart", "#22c55e"),
    SystemCategory("cafe", "Кафе и рестораны", "expense", "utensils", "#f97316", True),
    SystemCategory("delivery", "Доставка еды", "expense", "bike", "#fb923c", True),
    SystemCategory("transport", "Транспорт", "expense", "bus", "#3b82f6"),
    SystemCategory("taxi", "Такси", "expense", "car", "#facc15", True),
    SystemCategory("housing", "Жильё и аренда", "expense", "home", "#8b5cf6"),
    SystemCategory("utilities", "ЖКХ", "expense", "lightbulb", "#a855f7"),
    SystemCategory("communication", "Связь и интернет", "expense", "wifi", "#06b6d4"),
    SystemCategory("subscriptions", "Подписки", "expense", "repeat", "#ec4899", True),
    SystemCategory("marketplace", "Маркетплейсы", "expense", "package", "#d946ef", True),
    SystemCategory("clothes", "Одежда и обувь", "expense", "shirt", "#f43f5e", True),
    SystemCategory("health", "Здоровье", "expense", "heart-pulse", "#ef4444"),
    SystemCategory("entertainment", "Развлечения", "expense", "ticket", "#eab308", True),
    SystemCategory("education", "Образование", "expense", "graduation-cap", "#0ea5e9"),
    SystemCategory("kids", "Дети", "expense", "baby", "#14b8a6"),
    SystemCategory("credit", "Кредиты", "expense", "landmark", "#64748b"),
    SystemCategory("transfers", "Переводы", "expense", "arrow-right-left", "#78716c"),
    SystemCategory("other", "Прочее", "expense", "circle", "#94a3b8"),
    SystemCategory("salary", "Зарплата", "income", "wallet", "#16a34a"),
    SystemCategory("freelance", "Фриланс", "income", "laptop", "#0d9488"),
    SystemCategory("income_other", "Прочие доходы", "income", "plus-circle", "#65a30d"),
]


def ensure_system_categories(db: Session) -> None:
    """Идемпотентно создаёт/обновляет системные категории."""
    existing = {c.slug: c for c in db.scalars(select(Category))}
    for sc in SYSTEM_CATEGORIES:
        cat = existing.get(sc.slug)
        if cat is None:
            cat = Category(slug=sc.slug)
            db.add(cat)
        cat.name = sc.name
        cat.kind = sc.kind
        cat.icon = sc.icon
        cat.color = sc.color
        cat.is_discretionary = sc.is_discretionary
        cat.is_system = True
    db.commit()


def category_ids_by_slug(db: Session) -> dict[str, int]:
    return {c.slug: c.id for c in db.scalars(select(Category))}
