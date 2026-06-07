from app.collectors.base import DeviceConnector
from app.schemas.device import DeviceStatusRead


class ArubaConnector(DeviceConnector):
    connector_type = "aruba"

    async def poll(self, device_id: str) -> DeviceStatusRead:
        raise NotImplementedError("Aruba connector enabled in Phase 4 with MOCK_MODE=false")