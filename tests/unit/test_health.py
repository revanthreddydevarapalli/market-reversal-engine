def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app_name"] == "market-reversal-engine"
    assert body["environment"] == "test"
    assert "time_utc" in body
