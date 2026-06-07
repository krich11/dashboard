from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_import_devices_csv():
    csv_content = (
        "name,hostname,device_type,important_flag,management_ip,connector_enabled\n"
        "test-switch,sw01.example.com,juniper,true,10.0.0.50,true\n"
    )
    response = client.post(
        "/api/v1/devices/import",
        files={"file": ("devices.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 1

    devices = client.get("/api/v1/devices").json()
    imported = next((d for d in devices if d["name"] == "test-switch"), None)
    assert imported is not None
    assert imported["connector_enabled"] is True
    assert imported["credentials_configured"] is False


def test_poll_device_mock_mode():
    devices = client.get("/api/v1/devices").json()
    device_id = devices[0]["id"]
    response = client.post(f"/api/v1/devices/{device_id}/poll")
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == device_id
    assert body["overall"] in {"ok", "warning", "critical", "down", "unknown"}