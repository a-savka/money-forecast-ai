import datetime as dt

import pytest

from app.importers.screenshot import ScreenshotError, extract_transaction
from app.llm.base import RawCompletion, Usage
from app.llm.mock import MockProvider

TODAY = dt.date(2026, 10, 26)
PNG = b"\x89PNG\r\n\x1a\nfake-image"


def test_mock_is_deterministic():
    a = extract_transaction(MockProvider(), PNG, "image/png", TODAY)
    b = extract_transaction(MockProvider(), PNG, "image/png", TODAY)
    assert a.amount == b.amount < 0
    assert a.date == TODAY and a.merchant
    assert a.info["llm_provider"] == "mock"


class FakeVision:
    name, model = "fake", "fake-vision"

    def __init__(self, text: str):
        self.text = text

    def complete(self, system, user, *, schema=None):
        raise AssertionError("ожидался вызов с изображением")

    def complete_with_image(self, system, user, image, mime, *, schema=None):
        assert "YYYY-MM-DD" in system and mime == "image/jpeg"
        return RawCompletion(self.text, Usage(100, 20))


def test_parses_model_answer():
    answer = (
        '```json\n{"is_transaction": true, "amount": 520, "direction": "income", '
        '"date": "2026-10-24", "merchant": " Иван П. ", "bank_category": null, '
        '"confidence": 0.8}\n```'
    )
    res = extract_transaction(FakeVision(answer), b"jpg", "image/jpeg", TODAY)
    assert res.amount == 520 and res.date == dt.date(2026, 10, 24)
    assert res.merchant == "Иван П."


def test_future_or_bad_date_falls_back_to_today():
    answer = (
        '{"is_transaction": true, "amount": 99, "direction": "expense", '
        '"date": "2027-01-01", "merchant": "", "confidence": 0.4}'
    )
    res = extract_transaction(FakeVision(answer), b"jpg", "image/jpeg", TODAY)
    assert res.date == TODAY and res.amount == -99
    assert res.merchant == "Операция со скриншота"


def test_not_a_transaction():
    answer = '{"is_transaction": false, "amount": 0, "direction": "expense"}'
    with pytest.raises(ScreenshotError):
        extract_transaction(FakeVision(answer), b"jpg", "image/jpeg", TODAY)


def test_rejects_wrong_type():
    with pytest.raises(ScreenshotError):
        extract_transaction(MockProvider(), b"%PDF", "application/pdf", TODAY)


def test_api(client, auth):
    r = client.post(
        "/imports/receipt/image", files={"file": ("s.png", PNG, "image/png")}, headers=auth
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "screenshot" and body["amount"] < 0
    assert body["category_id"] and body["confidence"] == 0.9
    bad = client.post(
        "/imports/receipt/image", files={"file": ("a.txt", b"x", "text/plain")}, headers=auth
    )
    assert bad.status_code == 422
