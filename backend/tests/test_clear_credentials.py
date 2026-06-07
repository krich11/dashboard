from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_clear_credentials():
    created = client.post(
        "/api/v1/devices",
        json={
            "name": "cred-test",
            "hostname": "cred-test.example.com",
            "device_type": "linux_ssh",
            "username": "admin",
            "password": "secret",
        },
    )
    device_id = created.json()["id"]
    assert created.json()["credentials_configured"] is True

    updated = client.put(
        f"/api/v1/devices/{device_id}",
        json={"clear_credentials": True},
    )
    assert updated.json()["credentials_configured"] is False

    client.delete(f"/api/v1/devices/{device_id}")