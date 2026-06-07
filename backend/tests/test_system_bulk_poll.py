from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_system_info():
    info = client.get("/api/v1/system/info").json()
    assert info["version"] == "1.5.1"
    assert info["history_raw_days"] == 30
    assert info["history_hourly_days"] == 90
    assert info["mock_mode"] is True
    assert info["total_devices"] >= 67
    assert info["docs_url"] == "/docs"
    assert info["openapi_url"] == "/openapi.json"


def test_bulk_poll_devices():
    devices = client.get("/api/v1/devices").json()
    ids = [d["id"] for d in devices[:2]]
    client.post(
        "/api/v1/devices/bulk",
        json={"device_ids": ids, "connector_enabled": True},
    )
    response = client.post("/api/v1/devices/bulk-poll", json={"device_ids": ids})
    assert response.status_code == 200
    body = response.json()
    assert body["polled"] == 2
    assert len(body["results"]) == 2
    assert all(r["device_id"] in ids for r in body["results"])