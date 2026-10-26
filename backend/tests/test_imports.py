import io
import json
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.importers.statement import parse_amount, parse_statement

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-1 245,50", "-1245.50"),
        ("1,500.00", "1500.00"),
        ("−65", "-65"),
        ("300 ₽", "300"),
        ("", None),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == (Decimal(expected) if expected else None)


def test_tbank_preset_detected():
    res = parse_statement((FIXTURES / "tbank.csv").read_bytes(), "tbank.csv")
    assert res.preset == "tbank"
    assert len(res.rows) == 5  # FAILED пропущена
    assert res.skipped == 1
    assert res.rows[0].amount == Decimal("-1245.50")
    assert res.rows[0].mcc == "5411"
    assert res.rows[0].bank_category == "Супермаркеты"


def test_generic_debit_credit_columns():
    res = parse_statement((FIXTURES / "generic.csv").read_bytes(), "generic.csv")
    assert res.preset is None
    assert [r.amount for r in res.rows] == [Decimal("-350.00"), Decimal("1500.00")]
    assert res.skipped == 1


def _upload(client, auth, path, name=None, mapping=None):
    files = {"file": (name or path.name, path.read_bytes() if isinstance(path, Path) else path)}
    data = {"mapping": json.dumps(mapping)} if mapping else None
    return client.post("/imports/statement", files=files, data=data, headers=auth)


@pytest.fixture
def empty_auth(client):
    token = client.post("/auth/demo-login", json={}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_import_flow_and_dedup(client, empty_auth):
    preview = _upload(client, empty_auth, FIXTURES / "tbank.csv").json()
    assert preview["bank_name"] == "Т-Банк"
    assert preview["rows_total"] == 5
    assert preview["duplicates"] == 0
    assert preview["total_income"] == 52000

    res = client.post(f"/imports/{preview['job_id']}/confirm", json={}, headers=empty_auth).json()
    assert res["imported"] == 5  # две одинаковые покупки в один день — обе сохранены

    txs = client.get("/transactions", headers=empty_auth).json()["items"]
    cats = {c["id"]: c["slug"] for c in client.get("/categories").json()}
    by_desc = {t["description"]: cats[t["category_id"]] for t in txs}
    assert by_desc["Перекрёсток"] == "products"
    assert by_desc["Зарплата ООО Даталаб"] == "salary"

    again = _upload(client, empty_auth, FIXTURES / "tbank.csv").json()
    assert again["duplicates"] == 5
    res2 = client.post(
        f"/imports/{again['job_id']}/confirm",
        json={"account_id": res["account_id"]},
        headers=empty_auth,
    ).json()
    assert res2 == {**res2, "imported": 0, "skipped": 5}
    assert (
        client.post(f"/imports/{again['job_id']}/confirm", json={}, headers=empty_auth).status_code
        == 409
    )


def test_manual_mapping_and_excel(client, empty_auth):
    wb = Workbook()
    ws = wb.active
    ws.append(["Когда", "Что", "Сколько"])
    ws.append(["01.10.2026", "Пятёрочка", -500])
    ws.append(["02.10.2026", "Такси", -300])
    buf = io.BytesIO()
    wb.save(buf)

    files = {"file": ("st.xlsx", buf.getvalue())}
    unknown = client.post("/imports/statement", files=files, headers=empty_auth).json()
    assert unknown["mapping"] is None
    assert unknown["headers"] == ["Когда", "Что", "Сколько"]

    mapping = {"date": 0, "description": 1, "amount": 2}
    files = {"file": ("st.xlsx", buf.getvalue())}
    preview = client.post(
        "/imports/statement", files=files, data={"mapping": json.dumps(mapping)}, headers=empty_auth
    ).json()
    assert preview["rows_total"] == 2
    assert preview["total_expense"] == -800


def test_bad_file(client, empty_auth):
    files = {"file": ("x.csv", b"only header\n")}
    assert client.post("/imports/statement", files=files, headers=empty_auth).status_code == 422


def test_bank_mock_connect(client, empty_auth):
    banks = client.get("/imports/bank-mock/banks").json()
    assert {b["key"] for b in banks} >= {"tbank", "sber"}
    res = client.post(
        "/imports/bank-mock/connect", json={"bank": "sber", "months": 3}, headers=empty_auth
    ).json()
    assert res["imported"] > 100
    accounts = client.get("/accounts", headers=empty_auth).json()
    assert accounts[0]["name"] == "СберКарта"
    # Баланс положительный и правдоподобный
    assert 0 < accounts[0]["balance"] < 500_000
    assert (
        client.post(
            "/imports/bank-mock/connect", json={"bank": "nope"}, headers=empty_auth
        ).status_code
        == 404
    )
