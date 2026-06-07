from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_device_status_history_after_poll():
    devices = client.get("/api/v1/devices").json()
    device_id = devices[0]["id"]
    client.post(
        "/api/v1/devices/bulk",
        json={"device_ids": [device_id], "connector_enabled": True},
    )
    client.post(f"/api/v1/devices/{device_id}/poll")
    history = client.get(f"/api/v1/devices/{device_id}/status/history").json()
    assert len(history) >= 1
    assert history[-1]["device_id"] == device_id
    assert history[-1]["source"] in {"manual", "seed", "collector", "bulk"}


def test_operational_history_endpoint():
    response = client.get("/api/v1/status/history?hours=24")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_widget_catalog_includes_new_widgets():
    catalog = client.get("/api/v1/widgets/catalog").json()
    types = {w["type"] for w in catalog}
    assert "CollectorStatus" in types
    assert "SystemInfo" in types
    assert "DeviceHealthTrend" in types