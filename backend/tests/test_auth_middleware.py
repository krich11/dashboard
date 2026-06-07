import os

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_open_mode_without_api_key():
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200


def test_api_key_required_when_configured(monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_KEY", "test-secret-key")
    get_settings.cache_clear()
    try:
        gated = TestClient(app)
        denied = gated.get("/api/v1/system/info")
        assert denied.status_code == 401
        allowed = gated.get("/api/v1/system/info", headers={"X-API-Key": "test-secret-key"})
        assert allowed.status_code == 200
        health = gated.get("/health")
        assert health.status_code == 200
    finally:
        monkeypatch.delenv("DASHBOARD_API_KEY", raising=False)
        get_settings.cache_clear()