from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_prometheus_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "dashboard_important_devices_total" in response.text
    assert "dashboard_collector_running" in response.text


def test_alert_settings_roundtrip():
    payload = {
        "enabled": True,
        "webhook_url": "https://example.com/hook",
        "min_interval_sec": 120,
    }
    saved = client.put("/api/v1/settings/alerts", json=payload)
    assert saved.status_code == 200
    fetched = client.get("/api/v1/settings/alerts").json()
    assert fetched["enabled"] is True
    assert fetched["webhook_url"] == "https://example.com/hook"