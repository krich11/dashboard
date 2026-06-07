import asyncio
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.models.device import Device
from app.schemas.device import DeviceStatusRead
from app.services.crypto import decrypt_credentials
from app.services.normalization import build_status_message, normalize_overall


class ConnectorError(Exception):
    pass


class ConnectorSkipped(Exception):
    pass


def load_device(db: Session, device_id: str) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise ConnectorError(f"Unknown device {device_id}")
    return device


def device_target(device: Device) -> str:
    target = device.management_ip or device.hostname
    if not target:
        raise ConnectorError(f"No management IP or hostname for {device.name}")
    return target


def device_credentials(device: Device) -> tuple[str | None, str | None]:
    return decrypt_credentials(device.credentials_encrypted)


def make_status(
    device_id: str,
    overall: str,
    *,
    message: str | None = None,
    metrics: dict | None = None,
    details: dict | None = None,
) -> DeviceStatusRead:
    normalized = normalize_overall(overall)
    return DeviceStatusRead(
        device_id=device_id,
        overall=normalized,
        message=message or build_status_message(normalized),
        metrics=metrics or {},
        details=details or {},
        timestamp=datetime.now(UTC),
    )


async def ping_host(target: str, timeout_sec: int = 5) -> bool:
    proc = await asyncio.create_subprocess_exec(
        "ping",
        "-c",
        "1",
        "-W",
        str(timeout_sec),
        target,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    rc = await proc.wait()
    return rc == 0


async def http_get_json(
    url: str,
    *,
    username: str | None = None,
    password: str | None = None,
    timeout_sec: int = 15,
) -> dict:
    auth = (username, password) if username and password else None
    async with httpx.AsyncClient(verify=False, timeout=timeout_sec) as client:
        response = await client.get(url, auth=auth)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ConnectorError("Expected JSON object response")
        return data