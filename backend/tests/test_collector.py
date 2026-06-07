import pytest

from app.collectors.mock import MockConnector
from app.db.session import SessionLocal
from app.models.device import Device


@pytest.mark.asyncio
async def test_mock_connector_poll():
    db = SessionLocal()
    try:
        device = db.query(Device).first()
        connector = MockConnector(db)
        status = await connector.poll(device.id)
        assert status.device_id == device.id
        assert status.overall in {"ok", "warning", "critical", "down", "unknown"}
    finally:
        db.close()