import pytest
from pydantic import BaseModel

from app.llm.base import LLMError, RawCompletion, Usage, extract_json, structured_call
from app.llm.factory import get_provider


class Answer(BaseModel):
    value: int

    @classmethod
    def mock_response(cls, payload: dict) -> dict:
        return {"value": payload.get("x", 0) * 2}


class FlakyProvider:
    """Сначала отвечает мусором, потом — корректно."""

    name = "flaky"
    model = "f-1"

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def complete(self, system, user, *, schema=None):
        self.prompts.append(user)
        return RawCompletion(self.answers.pop(0), Usage(10, 5))

    def complete_with_image(self, system, user, image, mime, *, schema=None):
        return self.complete(system, user)


def test_extract_json():
    assert extract_json('Вот ответ:\n```json\n{"value": 1}\n```') == '{"value": 1}'
    with pytest.raises(LLMError):
        extract_json("нет json")


def test_mock_provider_uses_payload():
    res = structured_call(get_provider("mock"), "sys", 'Данные: {"x": 21}', Answer, use_cache=False)
    assert res.data.value == 42
    assert res.provider == "mock"


def test_retry_then_success():
    p = FlakyProvider(["не json", '{"value": 7}'])
    res = structured_call(p, "sys", "u", Answer, use_cache=False)
    assert res.data.value == 7 and res.attempts == 2
    assert res.usage.input_tokens == 20
    assert "не прошёл проверку" in p.prompts[1]


def test_gives_up_after_retries():
    p = FlakyProvider(['{"value": "abc"}', '{"wrong": 1}'])
    with pytest.raises(LLMError):
        structured_call(p, "sys", "u", Answer, use_cache=False)


def test_cache():
    p = FlakyProvider(['{"value": 1}'])
    first = structured_call(p, "sys", "same", Answer)
    second = structured_call(p, "sys", "same", Answer)
    assert not first.cached and second.cached and second.data.value == 1


def test_unconfigured_provider():
    with pytest.raises(LLMError):
        get_provider("gigachat")
