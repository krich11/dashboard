from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_mock_scenario_switch_updates_high_level():
    before = client.get("/api/v1/status/high-level").json()
    assert before["banner"] == "all_clear"

    response = client.put(
        "/api/v1/settings/mock-scenario",
        json={"scenario": "devices_down"},
    )
    assert response.status_code == 200
    assert response.json()["scenario"] == "devices_down"

    after = client.get("/api/v1/status/high-level").json()
    assert after["banner"] == "devices_down"
    assert after["important_down"] > 0

    client.put("/api/v1/settings/mock-scenario", json={"scenario": "all_clear"})