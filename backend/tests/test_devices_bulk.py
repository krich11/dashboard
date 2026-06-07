from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_bulk_enable_connectors():
    devices = client.get("/api/v1/devices").json()
    ids = [d["id"] for d in devices[:3]]
    response = client.post(
        "/api/v1/devices/bulk",
        json={"device_ids": ids, "connector_enabled": True},
    )
    assert response.status_code == 200
    assert response.json()["updated"] == 3

    refreshed = client.get("/api/v1/devices").json()
    enabled = {d["id"]: d["connector_enabled"] for d in refreshed if d["id"] in ids}
    assert all(enabled.values())


def test_collector_status_endpoint():
    status = client.get("/api/v1/settings/collector/status").json()
    assert "running" in status
    assert status["total_devices"] >= 67
    assert status["mock_mode"] is True