"""Mock connector stub — implemented in Phase 1."""

from app.collectors.base import DeviceConnector


class MockConnector(DeviceConnector):
    connector_type = "mock"

    async def poll(self, device_id: str):
        raise NotImplementedError("MockConnector implemented in Phase 1")