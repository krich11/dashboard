from sqlalchemy.orm import Session

from app.collectors.base import DeviceConnector
from app.collectors.helpers import (
    ConnectorError,
    device_credentials,
    device_target,
    http_get_json,
    load_device,
    make_status,
)
from app.schemas.device import DeviceStatusRead


class HpeILORestConnector(DeviceConnector):
    connector_type = "hpe_ilorest"

    def __init__(self, db: Session) -> None:
        self.db = db

    async def poll(self, device_id: str) -> DeviceStatusRead:
        device = load_device(self.db, device_id)
        target = device_target(device)
        username, password = device_credentials(device)
        if not username or not password:
            raise ConnectorError("HPE iLO credentials required")

        data = await http_get_json(
            f"https://{target}/redfish/v1/Systems/1",
            username=username,
            password=password,
        )
        health = (data.get("Status") or {}).get("Health", "Unknown")
        power = data.get("PowerState", "Unknown")
        overall = "ok" if str(health).lower() in {"ok", "good"} and str(power).lower() != "off" else "warning"
        if str(power).lower() == "off":
            overall = "down"

        return make_status(
            device_id,
            overall,
            message=f"HPE Redfish health={health}, power={power}",
            metrics={"power_state": power},
            details={"connector": self.connector_type, "redfish_health": health},
        )