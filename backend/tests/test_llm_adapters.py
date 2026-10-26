import json

import httpx
import pytest
from pydantic import BaseModel

from app.llm.base import LLMError, LLMNotSupported, structured_call
from app.llm.gigachat import GigaChatProvider
from app.llm.yandexgpt import YandexGPTProvider


class Answer(BaseModel):
    value: int


def test_gigachat_oauth_and_chat():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/oauth"):
            assert request.headers["Authorization"] == "Basic KEY"
            assert "RqUID" in request.headers
            return httpx.Response(200, json={"access_token": "tok", "expires_at": 9999999999999})
        assert request.headers["Authorization"] == "Bearer tok"
        body = json.loads(request.content)
        assert body["messages"][0]["role"] == "system"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '```json\n{"value": 5}\n```'}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 7},
            },
        )

    p = GigaChatProvider("KEY", transport=httpx.MockTransport(handler))
    res = structured_call(p, "sys", "user", Answer, use_cache=False)
    assert res.data.value == 5 and res.usage.input_tokens == 100
    structured_call(p, "sys", "user2", Answer, use_cache=False)
    # Токен переиспользуется
    assert sum(r.url.path.endswith("/oauth") for r in calls) == 1


def test_gigachat_error():
    p = GigaChatProvider(
        "KEY", transport=httpx.MockTransport(lambda r: httpx.Response(401, text="no"))
    )
    with pytest.raises(LLMError):
        p.complete("s", "u")


def test_yandexgpt():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Api-Key K"
        body = json.loads(request.content)
        assert body["modelUri"] == "gpt://F/yandexgpt-lite/latest"
        return httpx.Response(
            200,
            json={
                "result": {
                    "alternatives": [{"message": {"role": "assistant", "text": '{"value": 3}'}}],
                    "usage": {"inputTextTokens": "50", "completionTokens": "4"},
                }
            },
        )

    p = YandexGPTProvider("K", "F", transport=httpx.MockTransport(handler))
    res = structured_call(p, "s", "u", Answer, use_cache=False)
    assert res.data.value == 3 and res.usage.output_tokens == 4
    with pytest.raises(LLMNotSupported):
        p.complete_with_image("s", "u", b"img", "image/png")
