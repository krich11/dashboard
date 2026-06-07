from app.collectors.base import DeviceConnector
from app.schemas.device import DeviceStatusRead


class LinuxSSHConnector(DeviceConnector):
    connector_type = "linux_ssh"

    async def poll(self, device_id: str) -> DeviceStatusRead:
        raise NotImplementedError("Linux SSH connector enabled in Phase 4 with MOCK_MODE=false")