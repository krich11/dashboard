from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_export_import_roundtrip():
    default = client.get("/api/v1/dashboards/default").json()
    exported = client.get(f"/api/v1/dashboards/{default['id']}/export").json()
    assert exported["export_version"] == "1.0"
    assert len(exported["widgets"]) == 2

    exported["name"] = "Imported Copy"
    response = client.post(
        "/api/v1/dashboards/import",
        json={"dashboard": exported, "set_as_default": False},
    )
    assert response.status_code == 201
    imported = response.json()
    assert imported["name"] == "Imported Copy"
    assert len(imported["widgets"]) == 2
    assert {w["widget_type"] for w in imported["widgets"]} == {
        "UpDownOverallStatus",
        "InternetReachability",
    }
    exported_ids = {w["id"] for w in exported["widgets"]}
    imported_ids = {w["id"] for w in imported["widgets"]}
    assert imported_ids.isdisjoint(exported_ids)