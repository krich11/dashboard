from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.collectors.helpers import ConnectorSkipped
from app.db.session import get_db
from app.schemas.discovery import CredentialTestRequest, CredentialTestResult
from app.schemas.device import (
    BulkDeviceDelete,
    BulkDevicePoll,
    BulkDeviceUpdate,
    BulkPollResult,
    DeviceCreate,
    DeviceRead,
    DeviceStatusHistoryPoint,
    DeviceStatusRead,
    DeviceUpdate,
    DeviceWithStatus,
)
from app.services import status_history as status_history_service
from app.services import devices as device_service
from app.services import discovery_service

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.get("", response_model=list[DeviceRead])
def list_devices(
    important: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[DeviceRead]:
    return device_service.list_devices(db, important=important)


@router.get("/export", response_class=PlainTextResponse)
def export_devices(db: Session = Depends(get_db)) -> PlainTextResponse:
    content = device_service.export_devices_csv(db)
    return PlainTextResponse(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="devices-export.csv"'},
    )


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


@router.get("/{device_id}/status/history", response_model=list[DeviceStatusHistoryPoint])
def get_device_status_history(
    device_id: str,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> list[DeviceStatusHistoryPoint]:
    if device_service.get_device(db, device_id) is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return status_history_service.get_device_status_history(
        db, device_id, hours=hours, limit=limit
    )


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


@router.post("/bulk")
def bulk_update_devices(payload: BulkDeviceUpdate, db: Session = Depends(get_db)) -> dict:
    updated = device_service.bulk_update_devices(db, payload)
    return {"updated": updated}


@router.post("/bulk-delete")
def bulk_delete_devices(payload: BulkDeviceDelete, db: Session = Depends(get_db)) -> dict:
    deleted = device_service.bulk_delete_devices(db, payload)
    return {"deleted": deleted}


@router.post("/bulk-poll", response_model=BulkPollResult)
async def bulk_poll_devices(payload: BulkDevicePoll, db: Session = Depends(get_db)) -> BulkPollResult:
    return await device_service.bulk_poll_devices(db, payload.device_ids)


@router.post("/{device_id}/credentials/test", response_model=CredentialTestResult)
async def test_device_credentials(
    device_id: str,
    payload: CredentialTestRequest | None = None,
    db: Session = Depends(get_db),
) -> CredentialTestResult:
    body = payload or CredentialTestRequest()
    try:
        return await discovery_service.test_device_credentials(
            db,
            device_id,
            username=body.username,
            password=body.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{device_id}/poll", response_model=DeviceStatusRead)
async def poll_device_now(device_id: str, db: Session = Depends(get_db)) -> DeviceStatusRead:
    try:
        return await device_service.poll_device_now(db, device_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConnectorSkipped as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc