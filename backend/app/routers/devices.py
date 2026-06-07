from fastapi import APIRouter, Query

from app.schemas.device import DeviceRead
from app.services.mock_data import get_devices

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.get("", response_model=list[DeviceRead])
def list_devices(important: bool | None = Query(default=None)) -> list[DeviceRead]:
    devices = get_devices()
    if important is not None:
        devices = [d for d in devices if d.important_flag is important]
    return devices