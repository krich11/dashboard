from app.collectors.base import DeviceConnector
from app.schemas.device import DeviceStatusRead


class HpeILORestConnector(DeviceConnector):
    connector_type = "hpe_ilorest"

    async def poll(self, device_id: str) -> DeviceStatusRead:
        raise NotImplementedError("HPE iLO connector enabled in Phase 4 with MOCK_MODE=false")