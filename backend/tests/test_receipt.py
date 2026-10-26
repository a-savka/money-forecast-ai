from datetime import datetime
from decimal import Decimal

import pytest

from app.importers.receipt import ReceiptError, parse_receipt_qr

QR = "t=20261025T1942&s=1245.50&fn=7380440700076549&i=41975&fp=2026408802&n=1"


def test_parse_purchase():
    r = parse_receipt_qr(QR)
    assert r.timestamp == datetime(2026, 10, 25, 19, 42)
    assert r.amount == Decimal("-1245.50")
    assert r.fd == "41975"


def test_refund_is_positive():
    assert parse_receipt_qr(QR.replace("n=1", "n=2")).amount == Decimal("1245.50")


@pytest.mark.parametrize("bad", ["https://example.com", "t=xx&s=1", "t=20261025T1942&s=abc"])
def test_invalid(bad):
    with pytest.raises(ReceiptError):
        parse_receipt_qr(bad)


def test_receipt_endpoint(client, auth):
    draft = client.post("/imports/receipt/qr", json={"qr": QR}, headers=auth).json()
    assert draft["amount"] == -1245.5
    assert draft["date"] == "2026-10-25"
    cats = {c["id"]: c["slug"] for c in client.get("/categories").json()}
    assert cats[draft["category_id"]] == "products"
    assert (
        client.post("/imports/receipt/qr", json={"qr": "hello world"}, headers=auth).status_code
        == 422
    )
