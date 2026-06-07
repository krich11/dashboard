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