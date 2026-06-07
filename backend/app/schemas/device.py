from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceBase(BaseModel):
    name: str
    hostname: str
    device_type: str
    tags: list[str] = Field(default_factory=list)
    important_flag: bool = False
    management_ip: str | None = None
    connector_enabled: bool = False


class DeviceCreate(DeviceBase):
    username: str | None = None
    password: str | None = None


class BulkDeviceUpdate(BaseModel):
    device_ids: list[str]
    connector_enabled: bool | None = None
    important_flag: bool | None = None


class BulkDeviceDelete(BaseModel):
    device_ids: list[str]


class DeviceUpdate(BaseModel):
    name: str | None = None
    hostname: str | None = None
    device_type: str | None = None
    tags: list[str] | None = None
    important_flag: bool | None = None
    management_ip: str | None = None
    connector_enabled: bool | None = None
    username: str | None = None
    password: str | None = None
    clear_credentials: bool = False


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
    credentials_configured: bool = False

    @classmethod
    def from_device(cls, device) -> "DeviceRead":
        return cls(
            id=device.id,
            name=device.name,
            hostname=device.hostname,
            device_type=device.device_type,
            tags=device.tags or [],
            important_flag=device.important_flag,
            management_ip=device.management_ip,
            connector_enabled=device.connector_enabled,
            credentials_configured=bool(device.credentials_encrypted),
        )


class DeviceStatusRead(BaseModel):
    device_id: str
    overall: str
    message: str
    metrics: dict
    details: dict
    timestamp: datetime


class DeviceWithStatus(DeviceRead):
    status: DeviceStatusRead | None = None


class IssueItem(BaseModel):
    device_id: str
    device_name: str
    device_type: str
    overall: str
    message: str
    important_flag: bool
    timestamp: datetime