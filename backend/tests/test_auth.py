def test_demo_profiles(client):
    keys = [p["key"] for p in client.get("/auth/demo-profiles").json()]
    assert keys == ["young", "family", "freelancer", "dropout"]


def test_demo_login_seeds_once(client):
    r1 = client.post("/auth/demo-login", json={"profile": "young"})
    assert r1.status_code == 200
    r2 = client.post("/auth/demo-login", json={"profile": "young"})
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]
    token = r2.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["profile"] == "young"


def test_empty_user_and_unauthorized(client):
    r = client.post("/auth/demo-login", json={})
    assert r.json()["user"]["profile"] is None
    assert client.get("/auth/me").status_code == 401
    bad = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401


def test_unknown_profile(client):
    assert client.post("/auth/demo-login", json={"profile": "nope"}).status_code == 404
