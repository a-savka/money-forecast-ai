"""Распознавание операции на скриншоте банковского приложения через vision-LLM."""

import datetime as dt
import hashlib
import json
from dataclasses import dataclass

from app.llm.base import LLMProvider, structured_call
from app.llm.prompts import load_prompt
from app.llm.schemas import ScreenshotExtraction

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class ScreenshotError(ValueError):
    pass


@dataclass
class ScreenshotResult:
    date: dt.date
    amount: float  # со знаком: расход < 0
    merchant: str
    bank_category: str | None
    confidence: float
    info: dict


def extract_transaction(
    provider: LLMProvider, image: bytes, mime: str, today: dt.date
) -> ScreenshotResult:
    if mime not in ALLOWED_MIME:
        raise ScreenshotError("Поддерживаются изображения PNG, JPEG и WebP")
    if not image:
        raise ScreenshotError("Пустой файл")
    if len(image) > MAX_IMAGE_BYTES:
        raise ScreenshotError("Изображение больше 8 МБ")

    payload = {"today": today.isoformat(), "image_hash": hashlib.sha256(image).hexdigest()}
    res = structured_call(
        provider,
        load_prompt("screenshot_extract_v1"),
        f"Входные данные: {json.dumps(payload)}",
        ScreenshotExtraction,
        image=(image, mime),
    )
    data = res.data
    if not data.is_transaction or data.amount <= 0:
        raise ScreenshotError("Не нашли на изображении операцию — попробуйте другой скриншот")

    try:
        date = dt.date.fromisoformat(data.date) if data.date else today
    except ValueError:
        date = today
    if date > today:
        date = today
    return ScreenshotResult(
        date=date,
        amount=-data.amount if data.direction == "expense" else data.amount,
        merchant=data.merchant.strip() or "Операция со скриншота",
        bank_category=data.bank_category,
        confidence=data.confidence,
        info={
            "llm_provider": res.provider,
            "llm_model": res.model,
            "llm_latency_ms": res.latency_ms,
            "llm_tokens_in": res.usage.input_tokens,
            "llm_tokens_out": res.usage.output_tokens,
        },
    )
