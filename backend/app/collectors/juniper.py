import asyncio

from sqlalchemy.orm import Session

from app.collectors.base import DeviceConnector
from app.collectors.helpers import (
    ConnectorError,
    device_credentials,
    device_target,
    load_device,
    make_status,
)
from app.schemas.device import DeviceStatusRead


class JuniperConnector(DeviceConnector):
    connector_type = "juniper"

    def __init__(self, db: Session) -> None:
        self.db = db

    async def poll(self, device_id: str) -> DeviceStatusRead:
        device = load_device(self.db, device_id)
        target = device_target(device)
        username, password = device_credentials(device)
        if not username or not password:
            raise ConnectorError("Juniper credentials required")

        try:
            from jnpr.junos import Device as JunosDevice
        except ImportError as exc:
            raise ConnectorError("junos-eznc is required for Juniper polling") from exc

        def run() -> tuple[str, dict, str]:
            with JunosDevice(host=target, user=username, passwd=password, timeout=15) as dev:
                dev.open()
                facts = dev.facts
                hostname = facts.get("hostname", target)
                version = facts.get("version", "unknown")
                return "ok", {"version": version}, f"Juniper {hostname} reachable"

        overall, metrics, message = await asyncio.to_thread(run)
        return make_status(
            device_id,
            overall,
            message=message,
            metrics=metrics,
            details={"connector": self.connector_type},
        )