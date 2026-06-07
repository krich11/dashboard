from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.models.reachability import ExternalReachabilityResult

client = TestClient(app)


def test_collector_settings_roundtrip():
    payload = {
        "interval_sec": 120,
        "concurrency": 4,
        "default_backoff_sec": 45,
        "max_backoff_sec": 600,
        "circuit_breaker_threshold": 3,
        "status_staleness_sec": 300,
    }
    response = client.put("/api/v1/settings/collector", json=payload)
    assert response.status_code == 200
    assert response.json()["interval_sec"] == 120

    fetched = client.get("/api/v1/settings/collector").json()
    assert fetched["concurrency"] == 4


def test_encryption_status_and_test():
    status = client.get("/api/v1/settings/encryption").json()
    assert "configured" in status
    assert "is_dev_default" in status

    result = client.post(
        "/api/v1/settings/encryption/test",
        json={"test_value": "phase4-test"},
    ).json()
    assert result["ok"] is True


def test_reachability_history():
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        db.add(
            ExternalReachabilityResult(
                ipv4_ok=True,
                ipv6_ok=False,
                ipv4_targets=[],
                ipv6_targets=[],
                overall="degraded",
                timestamp=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
    finally:
        db.close()

    history = client.get("/api/v1/reachability/history?hours=24").json()
    assert len(history) >= 1
    assert "overall" in history[-1]


def test_history_settings_roundtrip():
    payload = {"raw_days": 14, "hourly_days": 60}
    response = client.put("/api/v1/settings/history", json=payload)
    assert response.status_code == 200
    assert response.json()["raw_days"] == 14

    fetched = client.get("/api/v1/settings/history").json()
    assert fetched["hourly_days"] == 60

    info = client.get("/api/v1/system/info").json()
    assert info["history_raw_days"] == 14
    assert info["history_hourly_days"] == 60


def test_history_settings_validation():
    response = client.put("/api/v1/settings/history", json={"raw_days": 90, "hourly_days": 30})
    assert response.status_code == 422


def test_widget_catalog():
    catalog = client.get("/api/v1/widgets/catalog").json()
    types = {w["type"] for w in catalog}
    assert "UpDownOverallStatus" in types
    assert "InternetHealthTrend" in types