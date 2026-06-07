from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_discovery_scan_mock_mode():
    response = client.post(
        "/api/v1/discovery/scan",
        json={"targets": ["10.0.0.50"], "username": "admin", "password": "secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scanned"] == 1
    assert body["candidates"][0]["reachable"] is True


def test_credential_test_mock_device():
    devices = client.get("/api/v1/devices").json()
    device_id = devices[0]["id"]
    client.put(
        f"/api/v1/devices/{device_id}",
        json={"connector_enabled": True},
    )
    result = client.post(f"/api/v1/devices/{device_id}/credentials/test", json={}).json()
    assert result["ok"] is True


def test_alert_events_list():
    client.put(
        "/api/v1/settings/alerts",
        json={
            "enabled": False,
            "webhook_url": "",
            "min_interval_sec": 300,
            "format": "json",
            "pagerduty_routing_key": "",
            "threshold_important_down": 1,
            "threshold_internet_degraded": True,
        },
    )
    client.get("/api/v1/status/high-level")
    events = client.get("/api/v1/settings/alerts/events").json()
    assert isinstance(events, list)