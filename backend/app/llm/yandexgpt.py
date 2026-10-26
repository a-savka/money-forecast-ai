"""Адаптер YandexGPT (Yandex Cloud Foundation Models).

Документация: https://yandex.cloud/ru/docs/foundation-models/
Нужны API-ключ сервисного аккаунта с ролью ai.languageModels.user и folder_id.
Работа с изображениями в этом API недоступна (для чеков нужен Vision OCR — вне MVP).
"""

from __future__ import annotations

import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.llm.base import LLMError, LLMNotSupported, RawCompletion, Usage

COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


class YandexGPTProvider:
    name = "yandexgpt"

    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model: str = "yandexgpt-lite",
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60,
    ):
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model
        self.client = httpx.Client(transport=transport, timeout=timeout)

    @classmethod
    def from_settings(cls) -> YandexGPTProvider:
        s = get_settings()
        return cls(s.yandex_api_key, s.yandex_folder_id, s.yandex_model)

    def complete(
        self, system: str, user: str, *, schema: type[BaseModel] | None = None
    ) -> RawCompletion:
        resp = self.client.post(
            COMPLETION_URL,
            headers={"Authorization": f"Api-Key {self.api_key}", "x-folder-id": self.folder_id},
            json={
                "modelUri": f"gpt://{self.folder_id}/{self.model}/latest",
                "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": "2000"},
                "messages": [{"role": "system", "text": system}, {"role": "user", "text": user}],
            },
        )
        if resp.status_code != 200:
            raise LLMError(f"YandexGPT: {resp.status_code} {resp.text[:200]}")
        result = resp.json()["result"]
        usage = result.get("usage", {})
        return RawCompletion(
            result["alternatives"][0]["message"]["text"],
            Usage(int(usage.get("inputTextTokens", 0)), int(usage.get("completionTokens", 0))),
        )

    def complete_with_image(
        self,
        system: str,
        user: str,
        image: bytes,
        mime: str,
        *,
        schema: type[BaseModel] | None = None,
    ) -> RawCompletion:
        raise LLMNotSupported("YandexGPT не принимает изображения")
