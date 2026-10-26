def test_events_and_time_to_value(client, auth):
    for seconds in (70, 95, 180):
        r = client.post(
            "/events", json={"name": "onboarding_done", "props": {"seconds": seconds}}, headers=auth
        )
        assert r.status_code == 204
    client.post("/events", json={"name": "paywall_shown"}, headers=auth)
    assert client.post("/events", json={"name": "hack"}, headers=auth).status_code == 422
    stats = client.get("/events/stats", headers=auth).json()
    assert stats["counts"] == {"onboarding_done": 3, "paywall_shown": 1}
    assert stats["onboarding_median_seconds"] == 95
    assert abs(stats["onboarding_under_2_min_share"] - 2 / 3) < 1e-9
