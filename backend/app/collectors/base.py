from abc import ABC, abstractmethod

from app.schemas.device import DeviceStatusRead


class DeviceConnector(ABC):
    connector_type: str

    @abstractmethod
    async def poll(self, device_id: str) -> DeviceStatusRead:
        raise NotImplementedError