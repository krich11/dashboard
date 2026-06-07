from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_export_devices_csv():
    response = client.get("/api/v1/devices/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.strip().splitlines()
    assert lines[0] == "name,hostname,device_type,tags,important_flag,management_ip,connector_enabled"
    assert len(lines) >= 68


def test_delete_device():
    created = client.post(
        "/api/v1/devices",
        json={
            "name": "delete-me",
            "hostname": "delete-me.example.com",
            "device_type": "linux_ssh",
        },
    )
    assert created.status_code == 201
    device_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/devices/{device_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/devices/{device_id}").status_code == 404


def test_bulk_delete_devices():
    ids = []
    for i in range(2):
        created = client.post(
            "/api/v1/devices",
            json={
                "name": f"bulk-del-{i}",
                "hostname": f"bulk-del-{i}.example.com",
                "device_type": "linux_ssh",
            },
        )
        ids.append(created.json()["id"])

    response = client.post("/api/v1/devices/bulk-delete", json={"device_ids": ids})
    assert response.status_code == 200
    assert response.json()["deleted"] == 2