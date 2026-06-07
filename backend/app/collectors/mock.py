from datetime import UTC, datetime
import random

from sqlalchemy.orm import Session

from app.collectors.base import DeviceConnector
from app.models.device import Device
from app.schemas.device import DeviceStatusRead
from app.services.mock_data import get_device_statuses
from app.services.mock_scenario import get_active_mock_scenario


class MockConnector(DeviceConnector):
    connector_type = "mock"

    def __init__(self, db: Session) -> None:
        self.db = db
        self._status_cache: dict[str, DeviceStatusRead] = {}
        self._cached_scenario: str | None = None

    def _load_cache(self) -> None:
        scenario = get_active_mock_scenario(self.db)
        if self._status_cache and self._cached_scenario == scenario:
            return
        self._status_cache = {}
        self._cached_scenario = scenario
        for status in get_device_statuses(scenario):
            self._status_cache[status.device_id] = status

    async def poll(self, device_id: str) -> DeviceStatusRead:
        device = self.db.get(Device, device_id)
        if device is None:
            raise ValueError(f"Unknown device {device_id}")

        self._load_cache()
        cached = self._status_cache.get(device_id)
        if cached:
            return DeviceStatusRead(
                device_id=device_id,
                overall=cached.overall,
                message=cached.message,
                metrics=dict(cached.metrics),
                details={**cached.details, "connector": "mock"},
                timestamp=datetime.now(UTC),
            )

        return DeviceStatusRead(
            device_id=device_id,
            overall="ok",
            message="Operational (generated mock)",
            metrics={"cpu_pct": random.randint(10, 70), "mem_pct": random.randint(20, 80)},
            details={"connector": "mock"},
            timestamp=datetime.now(UTC),
        )