"""Абстракция над LLM-провайдерами (GigaChat, YandexGPT, Mock).

Все обращения к LLM в приложении идут только через `structured_call`, который
просит JSON по Pydantic-схеме, валидирует ответ и один раз повторяет запрос с
описанием ошибки. Если и повтор не удался — бросается LLMError, и вызывающий
код откатывается на результат без LLM (например, стратегию H1).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, ValidationError

class LLMError(RuntimeError):
    pass


class LLMNotSupported(LLMError):
    pass


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class RawCompletion:
    text: str
    usage: Usage = field(default_factory=Usage)


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(
        self, system: str, user: str, *, schema: type[BaseModel] | None = None
    ) -> RawCompletion: ...

    def complete_with_image(
        self,
        system: str,
        user: str,
        image: bytes,
        mime: str,
        *,
        schema: type[BaseModel] | None = None,
    ) -> RawCompletion: ...


@dataclass
class LLMResult[T: BaseModel]:
    data: T
    provider: str
    model: str
    usage: Usage
    latency_ms: int
    attempts: int
    cached: bool = False


JSON_INSTRUCTION = (
    "Ответь ТОЛЬКО валидным JSON-объектом без пояснений и без markdown, "
    "строго по этой JSON-схеме:\n{schema}"
)


def extract_json(text: str) -> str:
    """Достаёт JSON-объект из ответа модели (убирает ```json-обёртки и текст вокруг)."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise LLMError("В ответе модели нет JSON-объекта")
    return text[start : end + 1]


_cache: dict[str, LLMResult] = {}
CACHE_SIZE = 256


def _cache_key(provider: LLMProvider, system: str, user: str, schema: type[BaseModel]) -> str:
    raw = f"{provider.name}|{provider.model}|{schema.__name__}|{system}|{user}"
    return hashlib.sha256(raw.encode()).hexdigest()


def structured_call[T: BaseModel](
    provider: LLMProvider,
    system: str,
    user: str,
    schema: type[T],
    *,
    image: tuple[bytes, str] | None = None,
    retries: int = 1,
    use_cache: bool = True,
) -> LLMResult[T]:
    key = _cache_key(provider, system, user, schema)
    if use_cache and image is None and key in _cache:
        hit = _cache[key]
        return LLMResult(hit.data, hit.provider, hit.model, Usage(), 0, 0, cached=True)

    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    full_system = f"{system}\n\n{JSON_INSTRUCTION.format(schema=schema_json)}"
    prompt = user
    usage = Usage()
    started = time.perf_counter()
    last_error = ""
    for attempt in range(1, retries + 2):
        if image is not None:
            raw = provider.complete_with_image(
                full_system, prompt, image[0], image[1], schema=schema
            )
        else:
            raw = provider.complete(full_system, prompt, schema=schema)
        usage.input_tokens += raw.usage.input_tokens
        usage.output_tokens += raw.usage.output_tokens
        try:
            data = schema.model_validate_json(extract_json(raw.text))
        except (LLMError, ValidationError) as exc:
            last_error = str(exc)[:500]
            prompt = (
                f"{user}\n\nПредыдущий ответ не прошёл проверку: {last_error}\n"
                "Исправь и верни только корректный JSON."
            )
            continue
        result = LLMResult(
            data=data,
            provider=provider.name,
            model=provider.model,
            usage=usage,
            latency_ms=int((time.perf_counter() - started) * 1000),
            attempts=attempt,
        )
        if use_cache and image is None:
            if len(_cache) >= CACHE_SIZE:
                _cache.pop(next(iter(_cache)))
            _cache[key] = result
        return result
    raise LLMError(f"Модель не вернула корректный JSON: {last_error}")
