import csv
import io
import uuid

from sqlalchemy.orm import Session, joinedload

from app.models.device import Device, LatestStatus
from app.schemas.device import (
    BulkDeviceDelete,
    BulkDeviceUpdate,
    BulkPollResult,
    DeviceCreate,
    DeviceRead,
    DeviceStatusRead,
    DeviceUpdate,
    DeviceWithStatus,
    IssueItem,
)
from app.collectors.factory import get_connector
from app.collectors.helpers import ConnectorSkipped
from app.services.crypto import decrypt_credentials, encrypt_credentials
from app.services.status_history import record_device_status


def to_device_read(device: Device) -> DeviceRead:
    return DeviceRead.from_device(device)


def list_devices(db: Session, important: bool | None = None) -> list[DeviceRead]:
    query = db.query(Device)
    if important is not None:
        query = query.filter(Device.important_flag.is_(important))
    return [to_device_read(d) for d in query.order_by(Device.name).all()]


def list_devices_with_status(
    db: Session,
    important: bool | None = None,
    device_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[DeviceWithStatus]:
    query = db.query(Device).options(joinedload(Device.latest_status))
    if important is not None:
        query = query.filter(Device.important_flag.is_(important))
    if device_type:
        query = query.filter(Device.device_type == device_type)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(
            (Device.name.ilike(like)) | (Device.hostname.ilike(like))
        )
    results: list[DeviceWithStatus] = []
    for device in query.order_by(Device.name).all():
        status_row = device.latest_status
        device_status = None
        if status_row:
            device_status = DeviceStatusRead(
                device_id=status_row.device_id,
                overall=status_row.overall,
                message=status_row.message,
                metrics=status_row.metrics,
                details=status_row.details,
                timestamp=status_row.timestamp,
            )
        if status and (device_status is None or device_status.overall != status):
            continue
        results.append(
            DeviceWithStatus(
                **to_device_read(device).model_dump(),
                status=device_status,
            )
        )
    return results


def get_device(db: Session, device_id: str) -> Device | None:
    return db.get(Device, device_id)


def get_device_status(db: Session, device_id: str) -> DeviceStatusRead | None:
    row = db.query(LatestStatus).filter(LatestStatus.device_id == device_id).first()
    if row is None:
        return None
    return DeviceStatusRead(
        device_id=row.device_id,
        overall=row.overall,
        message=row.message,
        metrics=row.metrics,
        details=row.details,
        timestamp=row.timestamp,
    )


def create_device(db: Session, payload: DeviceCreate) -> DeviceRead:
    device = Device(
        id=str(uuid.uuid4()),
        name=payload.name,
        hostname=payload.hostname,
        device_type=payload.device_type,
        tags=payload.tags,
        important_flag=payload.important_flag,
        management_ip=payload.management_ip,
        connector_enabled=payload.connector_enabled,
        credentials_encrypted=encrypt_credentials(payload.username, payload.password),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return to_device_read(device)


def update_device(db: Session, device_id: str, payload: DeviceUpdate) -> DeviceRead | None:
    device = db.get(Device, device_id)
    if device is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    username = data.pop("username", None)
    password = data.pop("password", None)
    clear_credentials = data.pop("clear_credentials", False)
    for key, value in data.items():
        setattr(device, key, value)
    if clear_credentials:
        device.credentials_encrypted = None
    elif username is not None or password is not None:
        existing_user, existing_pass = decrypt_credentials(device.credentials_encrypted)
        device.credentials_encrypted = encrypt_credentials(
            username if username is not None else existing_user,
            password if password is not None else existing_pass,
        )
    db.commit()
    db.refresh(device)
    return to_device_read(device)


async def bulk_poll_devices(db: Session, device_ids: list[str]) -> BulkPollResult:
    results: list[DeviceStatusRead] = []
    for device_id in device_ids:
        try:
            results.append(await poll_device_now(db, device_id, source="bulk"))
        except (ValueError, ConnectorSkipped):
            continue
    return BulkPollResult(polled=len(results), results=results)


async def poll_device_now(
    db: Session, device_id: str, *, source: str = "manual"
) -> DeviceStatusRead:
    device = db.get(Device, device_id)
    if device is None:
        raise ValueError("Device not found")
    connector = get_connector(db, device)
    status = await connector.poll(device_id)
    existing = db.query(LatestStatus).filter(LatestStatus.device_id == device_id).first()
    timestamp = status.timestamp.replace(tzinfo=None)
    if existing:
        existing.overall = status.overall
        existing.message = status.message
        existing.metrics = status.metrics
        existing.details = status.details
        existing.timestamp = timestamp
    else:
        db.add(
            LatestStatus(
                device_id=device_id,
                overall=status.overall,
                message=status.message,
                metrics=status.metrics,
                details=status.details,
                timestamp=timestamp,
            )
        )
    record_device_status(db, status, source=source)
    db.commit()
    return status


EXPORT_CSV_FIELDS = [
    "name",
    "hostname",
    "device_type",
    "tags",
    "important_flag",
    "management_ip",
    "connector_enabled",
]


def export_devices_csv(db: Session) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_CSV_FIELDS)
    writer.writeheader()
    for device in db.query(Device).order_by(Device.name).all():
        writer.writerow(
            {
                "name": device.name,
                "hostname": device.hostname,
                "device_type": device.device_type,
                "tags": ",".join(device.tags or []),
                "important_flag": "true" if device.important_flag else "false",
                "management_ip": device.management_ip or "",
                "connector_enabled": "true" if device.connector_enabled else "false",
            }
        )
    return buffer.getvalue()


def bulk_update_devices(db: Session, payload: BulkDeviceUpdate) -> int:
    if not payload.device_ids:
        return 0
    if payload.connector_enabled is None and payload.important_flag is None:
        return 0
    updated = 0
    for device_id in payload.device_ids:
        device = db.get(Device, device_id)
        if device is None:
            continue
        if payload.connector_enabled is not None:
            device.connector_enabled = payload.connector_enabled
        if payload.important_flag is not None:
            device.important_flag = payload.important_flag
        updated += 1
    db.commit()
    return updated


def delete_device(db: Session, device_id: str) -> bool:
    device = db.get(Device, device_id)
    if device is None:
        return False
    db.delete(device)
    db.commit()
    return True


def bulk_delete_devices(db: Session, payload: BulkDeviceDelete) -> int:
    deleted = 0
    for device_id in payload.device_ids:
        if delete_device(db, device_id):
            deleted += 1
    return deleted


def import_devices_csv(db: Session, content: str) -> int:
    reader = csv.DictReader(io.StringIO(content))
    count = 0
    for row in reader:
        payload = DeviceCreate(
            name=row.get("name", "").strip(),
            hostname=row.get("hostname", "").strip(),
            device_type=row.get("device_type", "linux_ssh").strip(),
            tags=[t.strip() for t in row.get("tags", "").split(",") if t.strip()],
            important_flag=row.get("important_flag", "").lower() in {"1", "true", "yes"},
            management_ip=row.get("management_ip") or None,
            connector_enabled=row.get("connector_enabled", "").lower() in {"1", "true", "yes"},
        )
        if payload.name and payload.hostname:
            create_device(db, payload)
            count += 1
    return count


def list_issues(db: Session, important_only: bool = False) -> list[IssueItem]:
    query = db.query(Device).options(joinedload(Device.latest_status))
    if important_only:
        query = query.filter(Device.important_flag.is_(True))
    issues: list[IssueItem] = []
    for device in query.all():
        status = device.latest_status
        if status is None or status.overall in {"ok"}:
            continue
        issues.append(
            IssueItem(
                device_id=device.id,
                device_name=device.name,
                device_type=device.device_type,
                overall=status.overall,
                message=status.message,
                important_flag=device.important_flag,
                timestamp=status.timestamp,
            )
        )
    return issues