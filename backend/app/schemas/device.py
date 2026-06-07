from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    hostname: str
    device_type: str
    tags: list[str]
    important_flag: bool
    management_ip: str | None
    connector_enabled: bool


class DeviceStatusRead(BaseModel):
    device_id: str
    overall: str
    message: str
    metrics: dict
    details: dict
    timestamp: datetime