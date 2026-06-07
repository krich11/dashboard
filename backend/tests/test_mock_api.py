from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.device import Device, LatestStatus
from datetime import UTC, datetime

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


def test_high_level_devices_down():
    db = SessionLocal()
    try:
        important = db.query(Device).filter(Device.important_flag.is_(True)).limit(3).all()
        for device in important:
            status = db.query(LatestStatus).filter(LatestStatus.device_id == device.id).first()
            status.overall = "down"
            status.message = "Unreachable"
            status.timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/status/high-level")
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


def test_reachability_settings_roundtrip():
    payload = {
        "ipv4_targets": ["1.1.1.1"],
        "ipv6_targets": ["2606:4700:4700::1111"],
        "interval_sec": 45,
        "timeout_sec": 3,
        "method": "ping",
        "require_both_families": False,
        "http_url_v4": "https://1.1.1.1",
        "http_url_v6": "https://[2606:4700:4700::1111]",
    }
    put = client.put("/api/v1/settings/reachability", json=payload)
    assert put.status_code == 200
    get = client.get("/api/v1/settings/reachability")
    assert get.status_code == 200
    assert get.json()["interval_sec"] == 45