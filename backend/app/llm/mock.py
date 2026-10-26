"""MOCK: детерминированный LLM-провайдер для разработки, тестов и демо без ключей.

Схема ответа определяет classmethod `mock_response(payload: dict) -> dict`,
где payload — JSON из запроса пользователя. Так мок отвечает осмысленно
(например, строит рекомендации из переданных агрегатов), а не фиксированной строкой.
"""

import json

from pydantic import BaseModel

from app.llm.base import LLMError, RawCompletion, Usage


class MockProvider:
    name = "mock"
    model = "mock-1"

    def complete(
        self, system: str, user: str, *, schema: type[BaseModel] | None = None
    ) -> RawCompletion:
        if schema is None or not hasattr(schema, "mock_response"):
            raise LLMError("Mock-провайдер не умеет отвечать без схемы с mock_response")
        text = json.dumps(schema.mock_response(_payload(user)), ensure_ascii=False)
        return RawCompletion(text, Usage(len(system + user) // 4, len(text) // 4))

    def complete_with_image(
        self,
        system: str,
        user: str,
        image: bytes,
        mime: str,
        *,
        schema: type[BaseModel] | None = None,
    ) -> RawCompletion:
        return self.complete(system, user, schema=schema)


def _payload(user: str) -> dict:
    start, end = user.find("{"), user.rfind("}")
    if start == -1:
        return {}
    try:
        return json.loads(user[start : end + 1])
    except json.JSONDecodeError:
        return {}
