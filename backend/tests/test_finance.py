import pytest


@pytest.fixture
def empty_auth(client):
    token = client.post("/auth/demo-login", json={}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _cat(client, slug):
    return next(c["id"] for c in client.get("/categories").json() if c["slug"] == slug)


def test_categories(client):
    cats = client.get("/categories").json()
    assert any(c["slug"] == "products" for c in cats)


def test_manual_transaction_creates_default_account(client, empty_auth):
    body = {
        "date": "2026-10-20",
        "amount": -450.5,
        "description": "Кофе",
        "category_id": _cat(client, "cafe"),
    }
    r = client.post("/transactions", json=body, headers=empty_auth)
    assert r.status_code == 201
    accounts = client.get("/accounts", headers=empty_auth).json()
    assert len(accounts) == 1
    assert accounts[0]["balance"] == -450.5


def test_crud_and_filters(client, empty_auth):
    h = empty_auth
    acc = client.post(
        "/accounts", json={"name": "Т-Банк", "balance_initial": 1000}, headers=h
    ).json()
    for amount, d, desc in [
        (-100, "2026-10-01", "Пятёрочка"),
        (-200, "2026-10-05", "Такси"),
        (5000, "2026-10-10", "ЗП"),
    ]:
        client.post(
            "/transactions",
            json={"account_id": acc["id"], "date": d, "amount": amount, "description": desc},
            headers=h,
        )

    page = client.get("/transactions", params={"kind": "expense"}, headers=h).json()
    assert page["total"] == 2
    assert page["items"][0]["description"] == "Такси"  # сортировка по дате desc

    page = client.get(
        # ilike по кириллице в SQLite регистрозависим, в Postgres — нет
        "/transactions",
        params={"q": "Пятёр", "from": "2026-10-01", "to": "2026-10-02"},
        headers=h,
    ).json()
    assert page["total"] == 1
    tx_id = page["items"][0]["id"]

    upd = client.patch(
        f"/transactions/{tx_id}", json={"category_id": _cat(client, "products")}, headers=h
    )
    assert upd.json()["category_source"] == "user"

    assert client.get("/accounts", headers=h).json()[0]["balance"] == 1000 - 100 - 200 + 5000
    assert client.delete(f"/transactions/{tx_id}", headers=h).status_code == 204
    assert client.get("/transactions", headers=h).json()["total"] == 2


def test_cannot_touch_foreign_data(client, auth, empty_auth):
    foreign = client.get("/transactions", params={"limit": 1}, headers=auth).json()["items"][0]
    assert client.delete(f"/transactions/{foreign['id']}", headers=empty_auth).status_code == 404
    assert (
        client.post(
            "/transactions",
            json={"account_id": foreign["account_id"], "date": "2026-10-01", "amount": -1},
            headers=empty_auth,
        ).status_code
        == 404
    )


def test_zero_amount_rejected(client, empty_auth):
    r = client.post("/transactions", json={"date": "2026-10-01", "amount": 0}, headers=empty_auth)
    assert r.status_code == 422


def test_auto_category_and_learning(client, empty_auth):
    h = empty_auth
    created = client.post(
        "/transactions",
        json={"date": "2026-10-01", "amount": -300, "description": "ВКУСВИЛЛ", "mcc": "5411"},
        headers=h,
    ).json()
    assert created["category_id"] == _cat(client, "products")
    assert created["category_source"] == "keyword"

    other = client.post(
        "/transactions",
        json={"date": "2026-10-02", "amount": -500, "description": "ВКУСВИЛЛ"},
        headers=h,
    ).json()
    # Пользователь считает ВкусВилл кафе → правило и перекатегоризация похожих
    client.patch(
        f"/transactions/{created['id']}", json={"category_id": _cat(client, "cafe")}, headers=h
    )
    items = client.get("/transactions", headers=h).json()["items"]
    by_id = {t["id"]: t for t in items}
    assert by_id[other["id"]]["category_id"] == _cat(client, "cafe")

    s = client.get(
        "/categories/suggest", params={"description": "вкусвилл у дома", "amount": -10}, headers=h
    ).json()
    assert s["category"]["slug"] == "cafe"
    assert s["source"] == "rule"
