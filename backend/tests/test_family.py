def _login(client, profile):
    token = client.post("/auth/demo-login", json={"profile": profile}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_family_flow(client, auth):
    assert client.get("/mock/family", headers=auth).json() is None
    # Создание семьи — Premium
    assert client.post("/mock/family", json={"name": "Мы"}, headers=auth).status_code == 402
    client.post("/mock/subscription", json={"action": "start_trial"}, headers=auth)
    fam = client.post("/mock/family", json={"name": "Мы"}, headers=auth).json()
    assert fam["my_role"] == "owner" and len(fam["invite_code"]) == 6
    assert fam["members"][0]["is_me"] and fam["members"][0]["balance"] != 0

    # Второй пользователь присоединяется по коду (без Premium)
    other = _login(client, "dropout")
    joined = client.post(
        "/mock/family/join", json={"code": fam["invite_code"].lower()}, headers=other
    ).json()
    assert joined["my_role"] == "member" and len(joined["members"]) == 2
    total = sum(m["balance"] for m in joined["members"])
    assert abs(joined["total_balance"] - total) < 0.01
    again = client.post("/mock/family/join", json={"code": fam["invite_code"]}, headers=other)
    assert again.status_code == 409

    # Демо-участник добавляется из свободных демо-профилей
    with_demo = client.post("/mock/family/demo-member", headers=auth).json()
    assert len(with_demo["members"]) == 3

    # Участник выходит, владелец распускает семью
    client.post("/mock/family/leave", headers=other)
    assert len(client.get("/mock/family", headers=auth).json()["members"]) == 2
    client.post("/mock/family/leave", headers=auth)
    assert client.get("/mock/family", headers=auth).json() is None


def test_wrong_code(client, auth):
    r = client.post("/mock/family/join", json={"code": "ZZZZZZ"}, headers=auth)
    assert r.status_code == 409
