from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_default_dashboard_has_priority_widgets():
    response = client.get("/api/v1/dashboards/default")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Overview"
    types = {w["widget_type"] for w in body["widgets"]}
    assert "UpDownOverallStatus" in types
    assert "InternetReachability" in types


def test_devices_with_status_count():
    response = client.get("/api/v1/devices/with-status")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 67
    assert body[0]["status"] is not None