"""Схемы структурированных ответов LLM.

У каждой схемы есть `mock_response` — детерминированный ответ MockProvider,
построенный по тем же входным данным, что получает настоящая модель.
"""

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
