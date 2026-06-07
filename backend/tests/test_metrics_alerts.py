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
        "format": "slack",
    }
    saved = client.put("/api/v1/settings/alerts", json=payload)
    assert saved.status_code == 200
    fetched = client.get("/api/v1/settings/alerts").json()
    assert fetched["enabled"] is True
    assert fetched["format"] == "slack"


def test_slack_payload_builder():
    from datetime import UTC, datetime

    from app.schemas.status import HighLevelSummary
    from app.services.alert_service import build_slack_payload

    summary = HighLevelSummary(
        banner="devices_down",
        banner_text="3 Important Devices Down",
        important_total=10,
        important_up=7,
        important_down=3,
        internet_health="ok",
        internet_summary="IPv4 OK, IPv6 OK",
        worst_overall="critical",
        timestamp=datetime.now(UTC),
    )
    payload = build_slack_payload(summary)
    assert "blocks" in payload
    assert "3 Important Devices Down" in payload["blocks"][0]["text"]["text"]


def test_alert_test_without_url():
    client.put("/api/v1/settings/alerts", json={"enabled": False, "webhook_url": ""})
    result = client.post("/api/v1/settings/alerts/test").json()
    assert result["ok"] is False


def test_pagerduty_payload_builder():
    from datetime import UTC, datetime

    from app.schemas.settings import AlertSettings
    from app.schemas.status import HighLevelSummary
    from app.services.alert_service import build_pagerduty_payload

    summary = HighLevelSummary(
        banner="mixed",
        banner_text="Mixed outage",
        important_total=5,
        important_up=2,
        important_down=3,
        internet_health="degraded",
        internet_summary="IPv4 OK, IPv6 Down",
        worst_overall="critical",
        timestamp=datetime.now(UTC),
    )
    payload = build_pagerduty_payload(
        AlertSettings(pagerduty_routing_key="test-key"), summary
    )
    assert payload["routing_key"] == "test-key"
    assert payload["payload"]["severity"] == "critical"


def test_collector_run_once():
    result = client.post("/api/v1/settings/collector/run")
    assert result.status_code == 200
    body = result.json()
    assert body["devices_polled"] >= 67
    assert body["reachability"] is True


def test_banner_code_metric():
    response = client.get("/metrics")
    assert "dashboard_banner_code" in response.text