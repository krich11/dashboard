from sqlalchemy.orm import Session

from app.collectors.aruba import ArubaConnector
from app.collectors.base import DeviceConnector
from app.collectors.helpers import ConnectorError, ConnectorSkipped
from app.collectors.hpe_ilorest import HpeILORestConnector
from app.collectors.juniper import JuniperConnector
from app.collectors.linux_ssh import LinuxSSHConnector
from app.collectors.mock import MockConnector
from app.config import get_settings
from app.models.device import Device

CONNECTOR_BY_TYPE: dict[str, type[DeviceConnector]] = {
    "hpe_ilorest": HpeILORestConnector,
    "juniper": JuniperConnector,
    "aruba": ArubaConnector,
    "linux_ssh": LinuxSSHConnector,
}


def get_connector(db: Session, device: Device) -> DeviceConnector:
    settings = get_settings()
    if settings.mock_mode:
        return MockConnector(db)

    if not device.connector_enabled:
        raise ConnectorSkipped(f"Connector disabled for {device.name}")

    connector_cls = CONNECTOR_BY_TYPE.get(device.device_type)
    if connector_cls is None:
        raise ConnectorError(f"Unsupported device type: {device.device_type}")

    return connector_cls(db)