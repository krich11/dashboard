from app.collectors.base import DeviceConnector
from app.schemas.device import DeviceStatusRead


class JuniperConnector(DeviceConnector):
    connector_type = "juniper"

    async def poll(self, device_id: str) -> DeviceStatusRead:
        raise NotImplementedError("Juniper connector enabled in Phase 4 with MOCK_MODE=false")