from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mock_mode"] is True


def test_high_level_all_clear():
    response = client.get("/api/v1/status/high-level")
    assert response.status_code == 200
    body = response.json()
    assert body["banner"] == "all_clear"
    assert body["important_total"] == 17


def test_high_level_devices_down_scenario():
    response = client.get("/api/v1/status/high-level", params={"scenario": "devices_down"})
    assert response.status_code == 200
    body = response.json()
    assert body["banner"] == "devices_down"
    assert body["important_down"] == 3


def test_reachability_latest():
    response = client.get("/api/v1/reachability/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["ipv4_ok"] is True
    assert len(body["ipv4_targets"]) == 2


def test_devices_list_count():
    response = client.get("/api/v1/devices")
    assert response.status_code == 200
    assert len(response.json()) == 67


def test_devices_important_filter():
    response = client.get("/api/v1/devices", params={"important": True})
    assert response.status_code == 200
    assert len(response.json()) == 17