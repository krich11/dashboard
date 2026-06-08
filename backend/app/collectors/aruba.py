from sqlalchemy.orm import Session

from app.collectors.base import DeviceConnector
from app.collectors.helpers import (
    ConnectorError,
    device_credentials,
    device_target,
    http_get_json,
    load_device,
    make_status,
    ping_host,
)
from app.schemas.device import DeviceStatusRead


class ArubaConnector(DeviceConnector):
    connector_type = "aruba"

    def __init__(self, db: Session) -> None:
        self.db = db

    async def poll(self, device_id: str) -> DeviceStatusRead:
        device = load_device(self.db, device_id)
        target = device_target(device)
        username, password = device_credentials(device)

        if username and password:
            try:
                data = await http_get_json(
                    f"https://{target}/rest/v1/system",
                    username=username,
                    password=password,
                )
                status = str(data.get("status", data.get("operational_state", "ok"))).lower()
                overall = "ok" if status in {"ok", "up", "online", "running"} else "warning"
                return make_status(
                    device_id,
                    overall,
                    message=f"Aruba REST status={status}",
                    details={"connector": self.connector_type, "method": "rest"},
                )
            except Exception:
                pass

        reachable, _latency = await ping_host(target)
        if not reachable:
            return make_status(
                device_id,
                "down",
                message="Aruba host unreachable",
                details={"connector": self.connector_type, "method": "ping"},
            )
        return make_status(
            device_id,
            "ok",
            message="Aruba host reachable via ping",
            details={"connector": self.connector_type, "method": "ping"},
        )