from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.collectors.helpers import ConnectorSkipped
from app.db.session import get_db
from app.schemas.device import DeviceCreate, DeviceRead, DeviceStatusRead, DeviceUpdate, DeviceWithStatus
from app.services import devices as device_service

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.get("", response_model=list[DeviceRead])
def list_devices(
    important: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[DeviceRead]:
    return device_service.list_devices(db, important=important)


@router.get("/with-status", response_model=list[DeviceWithStatus])
def list_devices_with_status(
    important: bool | None = Query(default=None),
    device_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[DeviceWithStatus]:
    return device_service.list_devices_with_status(
        db,
        important=important,
        device_type=device_type,
        status=status,
        search=search,
    )


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: str, db: Session = Depends(get_db)) -> DeviceRead:
    device = device_service.get_device(db, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device_service.to_device_read(device)


@router.get("/{device_id}/status", response_model=DeviceStatusRead)
def get_device_status(device_id: str, db: Session = Depends(get_db)) -> DeviceStatusRead:
    status = device_service.get_device_status(db, device_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Status not found")
    return status


@router.post("", response_model=DeviceRead, status_code=201)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)) -> DeviceRead:
    return device_service.create_device(db, payload)


@router.put("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: str, payload: DeviceUpdate, db: Session = Depends(get_db)
) -> DeviceRead:
    device = device_service.update_device(db, device_id, payload)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: str, db: Session = Depends(get_db)) -> None:
    if not device_service.delete_device(db, device_id):
        raise HTTPException(status_code=404, detail="Device not found")


@router.post("/import")
def import_devices(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    content = file.file.read().decode("utf-8")
    count = device_service.import_devices_csv(db, content)
    return {"imported": count}


@router.post("/{device_id}/poll", response_model=DeviceStatusRead)
async def poll_device_now(device_id: str, db: Session = Depends(get_db)) -> DeviceStatusRead:
    try:
        return await device_service.poll_device_now(db, device_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConnectorSkipped as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc