"""Схемы структурированных ответов LLM.

У каждой схемы есть `mock_response` — детерминированный ответ MockProvider,
построенный по тем же входным данным, что получает настоящая модель.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CategoryAdjustment(BaseModel):
    category: str = Field(description="slug категории из входных данных")
    factor: float = Field(ge=0.5, le=1.5, description="множитель прогноза, 0.7–1.3")
    reason: str


class ForecastAdjustment(BaseModel):
    adjustments: list[CategoryAdjustment]
    summary: str

    @classmethod
    def mock_response(cls, payload: dict) -> dict:
        adjustments = []
        cats = payload.get("categories", [])
        holidays = payload.get("holidays_in_horizon", [])
        month = payload.get("horizon_month")
        for c in cats:
            slug, trend = c.get("slug"), c.get("trend_2w_vs_avg", 1.0)
            if trend >= 1.35 and c.get("forecast", 0) > 500:
                adjustments.append(
                    {
                        "category": slug,
                        "factor": 1.15,
                        "reason": "Последние две недели траты заметно выше обычного",
                    }
                )
            elif trend <= 0.6 and c.get("forecast", 0) > 500:
                adjustments.append(
                    {
                        "category": slug,
                        "factor": 0.9,
                        "reason": "Последние две недели вы тратите меньше обычного",
                    }
                )
            elif holidays and slug in {"cafe", "entertainment", "delivery"}:
                adjustments.append(
                    {
                        "category": slug,
                        "factor": 1.1,
                        "reason": f"Праздники в периоде: {', '.join(holidays)}",
                    }
                )
            elif month == 12 and slug in {"marketplace", "clothes"}:
                adjustments.append(
                    {"category": slug, "factor": 1.2, "reason": "Декабрь — время подарков"}
                )
        if adjustments:
            names = ", ".join(
                c["name"] for c in cats if c["slug"] in {a["category"] for a in adjustments}
            )
            summary = (
                f"Скорректировали прогноз по категориям: {names}. "
                "Остальное — по вашей обычной динамике."
            )
        else:
            summary = "Траты идут в обычном для вас темпе — прогноз совпадает со статистическим."
        return {"adjustments": adjustments, "summary": summary}


class RewrittenRecommendation(BaseModel):
    id: str
    title: str
    text: str


class RecommendationsRewrite(BaseModel):
    items: list[RewrittenRecommendation]

    @classmethod
    def mock_response(cls, payload: dict) -> dict:
        # Мок сохраняет порядок и тексты правил, добавляя мягкую формулировку
        return {
            "items": [
                {"id": r["id"], "title": r["title"], "text": r["text"]}
                for r in payload.get("recommendations", [])
            ]
        }


# MOCK: без реальной vision-модели мок не видит картинку и возвращает одну из типовых
# операций (выбор по хэшу изображения — один и тот же скриншот даёт один результат).
# В реальной версии поля заполняет GigaChat по изображению.
MOCK_SCREENSHOTS = [
    ("ВКУСВИЛЛ", 1247.50, "Супермаркеты"),
    ("Яндекс Такси", 389.00, "Транспорт"),
    ("Кофемания", 640.00, "Рестораны"),
    ("OZON", 2199.00, "Маркетплейсы"),
]


class ScreenshotExtraction(BaseModel):
    """Операция, распознанная на скриншоте банковского приложения."""

    is_transaction: bool = Field(description="На изображении есть операция по карте/счёту")
    amount: float = Field(ge=0, description="Сумма операции в рублях, без знака")
    direction: Literal["expense", "income"] = Field(description="Списание или поступление")
    date: str | None = Field(None, description="Дата операции YYYY-MM-DD, если видна")
    merchant: str = Field("", description="Название магазина/получателя/отправителя")
    bank_category: str | None = Field(None, description="Категория, как её подписал банк")
    confidence: float = Field(0.5, ge=0, le=1, description="Уверенность распознавания 0..1")

    @classmethod
    def mock_response(cls, payload: dict) -> dict:
        merchant, amount, category = MOCK_SCREENSHOTS[
            int(payload.get("image_hash", "0")[:8] or "0", 16) % len(MOCK_SCREENSHOTS)
        ]
        return {
            "is_transaction": True,
            "amount": amount,
            "direction": "expense",
            "date": payload.get("today"),
            "merchant": merchant,
            "bank_category": category,
            "confidence": 0.9,
        }
