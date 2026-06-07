import pytest

from app.collectors.factory import get_connector
from app.collectors.helpers import ConnectorSkipped
from app.collectors.mock import MockConnector
from app.config import get_settings
from app.db.session import SessionLocal
from app.models.device import Device


def test_factory_uses_mock_in_mock_mode():
    db = SessionLocal()
    try:
        device = db.query(Device).first()
        connector = get_connector(db, device)
        assert isinstance(connector, MockConnector)
    finally:
        db.close()


def test_factory_skips_disabled_device_when_not_mock(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    get_settings.cache_clear()
    db = SessionLocal()
    try:
        device = db.query(Device).first()
        device.connector_enabled = False
        with pytest.raises(ConnectorSkipped):
            get_connector(db, device)
    finally:
        db.close()
        monkeypatch.setenv("MOCK_MODE", "true")
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_linux_ping_fallback_without_credentials(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    get_settings.cache_clear()
    db = SessionLocal()
    try:
        from app.collectors.linux_ssh import LinuxSSHConnector

        device = db.query(Device).filter(Device.device_type == "linux_ssh").first()
        device.connector_enabled = True
        device.credentials_encrypted = None
        device.management_ip = "127.0.0.1"

        async def always_ping(_target: str, timeout_sec: int = 5) -> bool:
            return True

        monkeypatch.setattr("app.collectors.linux_ssh.ping_host", always_ping)
        status = await LinuxSSHConnector(db).poll(device.id)
        assert status.overall == "ok"
        assert status.details.get("method") == "ping"
    finally:
        db.close()
        monkeypatch.setenv("MOCK_MODE", "true")
        get_settings.cache_clear()