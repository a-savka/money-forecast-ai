"""Адаптер GigaChat (Сбер).

Авторизация: ключ авторизации (Basic) → OAuth-токен на 30 минут.
Документация: https://developers.sber.ru/docs/ru/gigachat/api/overview
Сертификаты API выпущены НУЦ Минцифры: установите корневой сертификат в систему
или укажите путь в GIGACHAT_CA_BUNDLE (для учебного стенда можно GIGACHAT_VERIFY_SSL=false).
"""

from __future__ import annotations

import time
import uuid

import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.llm.base import LLMError, RawCompletion, Usage

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://gigachat.devices.sberbank.ru/api/v1"


class GigaChatProvider:
    name = "gigachat"

    def __init__(
        self,
        auth_key: str,
        scope: str = "GIGACHAT_API_PERS",
        model: str = "GigaChat",
        *,
        verify: bool | str = True,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60,
    ):
        self.auth_key = auth_key
        self.scope = scope
        self.model = model
        self.client = httpx.Client(verify=verify, transport=transport, timeout=timeout)
        self._token: str | None = None
        self._token_expires = 0.0

    @classmethod
    def from_settings(cls) -> GigaChatProvider:
        s = get_settings()
        verify: bool | str = s.gigachat_ca_bundle or s.gigachat_verify_ssl
        return cls(s.gigachat_auth_key, s.gigachat_scope, s.gigachat_model, verify=verify)

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        resp = self.client.post(
            OAUTH_URL,
            headers={
                "Authorization": f"Basic {self.auth_key}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"scope": self.scope},
        )
        if resp.status_code != 200:
            raise LLMError(f"GigaChat OAuth: {resp.status_code} {resp.text[:200]}")
        body = resp.json()
        self._token = body["access_token"]
        self._token_expires = body.get("expires_at", 0) / 1000 or time.time() + 1500
        return self._token

    def _chat(self, messages: list[dict]) -> RawCompletion:
        resp = self.client.post(
            f"{API_URL}/chat/completions",
            headers={"Authorization": f"Bearer {self._access_token()}"},
            json={"model": self.model, "messages": messages, "temperature": 0.2},
        )
        if resp.status_code != 200:
            raise LLMError(f"GigaChat: {resp.status_code} {resp.text[:200]}")
        body = resp.json()
        usage = body.get("usage", {})
        return RawCompletion(
            body["choices"][0]["message"]["content"],
            Usage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)),
        )

    def complete(
        self, system: str, user: str, *, schema: type[BaseModel] | None = None
    ) -> RawCompletion:
        return self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
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
        upload = self.client.post(
            f"{API_URL}/files",
            headers={"Authorization": f"Bearer {self._access_token()}"},
            files={"file": ("image", image, mime)},
            data={"purpose": "general"},
        )
        if upload.status_code != 200:
            raise LLMError(f"GigaChat files: {upload.status_code} {upload.text[:200]}")
        file_id = upload.json()["id"]
        return self._chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user, "attachments": [file_id]},
            ]
        )
