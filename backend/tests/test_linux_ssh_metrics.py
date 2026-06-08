import pytest

from app.collectors.linux_ssh import LinuxSSHConnector
from app.config import get_settings
from app.db.session import SessionLocal
from app.models.device import Device


@pytest.mark.asyncio
async def test_linux_ssh_skips_non_loadavg_lines(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    get_settings.cache_clear()
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.device_type == "linux_ssh").first()
        device.connector_enabled = True
        device.credentials_encrypted = None
        device.management_ip = "127.0.0.1"

        def fake_run() -> tuple[str, dict]:
            return "ok", {
                "load_1m": 0.15,
                "mem_used_mb": 512,
                "mem_total_mb": 1024,
                "mem_pct": 50.0,
            }

        async def fake_poll_paramiko(self, device_id, target, username, password):
            from app.collectors.helpers import make_status

            overall, metrics = fake_run()
            return make_status(
                device_id,
                overall,
                message="Linux SSH poll succeeded",
                metrics=metrics,
                details={"connector": "linux_ssh", "method": "ssh"},
            )

        monkeypatch.setattr(LinuxSSHConnector, "_poll_paramiko", fake_poll_paramiko)
        device.credentials_encrypted = "enc"
        monkeypatch.setattr(
            "app.collectors.linux_ssh.device_credentials",
            lambda _device: ("user", "pass"),
        )
        status = await LinuxSSHConnector(db).poll(device.id)
        assert status.overall == "ok"
        assert status.metrics["load_1m"] == 0.15
    finally:
        db.close()
        monkeypatch.setenv("MOCK_MODE", "true")
        get_settings.cache_clear()