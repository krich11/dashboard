from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_credential_profiles_crud():
    empty = client.get("/api/v1/settings/credential-profiles").json()
    assert empty["profiles"] == []

    saved = client.put(
        "/api/v1/settings/credential-profiles",
        json=[
            {
                "name": "Linux default",
                "username": "root",
                "password": "linux-secret",
                "device_types": ["linux_ssh"],
                "enabled": True,
            },
            {
                "name": "Juniper ops",
                "username": "admin",
                "password": "juniper-secret",
                "device_types": ["juniper"],
                "enabled": True,
            },
        ],
    )
    assert saved.status_code == 200
    body = saved.json()
    assert len(body["profiles"]) == 2
    assert body["profiles"][0]["password_configured"] is True
    assert body["profiles"][0]["username"] == "root"

    profile_id = body["profiles"][0]["id"]
    updated = client.put(
        "/api/v1/settings/credential-profiles",
        json=[
            {
                "id": profile_id,
                "name": "Linux default",
                "username": "root",
                "device_types": ["linux_ssh"],
                "enabled": True,
            },
            {
                "name": "Juniper ops",
                "username": "admin",
                "password": "juniper-secret",
                "device_types": ["juniper"],
                "enabled": True,
            },
        ],
    )
    assert updated.status_code == 200
    assert updated.json()["profiles"][0]["password_configured"] is True


def test_discovery_scan_uses_credential_profiles_mock_mode():
    client.put(
        "/api/v1/settings/credential-profiles",
        json=[
            {
                "name": "Linux default",
                "username": "root",
                "password": "linux-secret",
                "device_types": ["linux_ssh"],
            }
        ],
    )
    response = client.post(
        "/api/v1/discovery/scan",
        json={"use_default_ranges": False, "targets": ["10.0.0.77"], "use_credential_profiles": True},
    )
    assert response.status_code == 200
    candidate = response.json()["candidates"][0]
    assert candidate["credentials_ok"] is True
    assert candidate["matched_credential_profile_name"] == "Linux default"