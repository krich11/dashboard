import csv
import io
import uuid

from sqlalchemy.orm import Session, joinedload

from app.models.device import Device, LatestStatus
from app.schemas.device import (
    DeviceCreate,
    DeviceRead,
    DeviceStatusRead,
    DeviceUpdate,
    DeviceWithStatus,
    IssueItem,
)
from app.services.crypto import decrypt_credentials, encrypt_credentials


def list_devices(db: Session, important: bool | None = None) -> list[DeviceRead]:
    query = db.query(Device)
    if important is not None:
        query = query.filter(Device.important_flag.is_(important))
    return [DeviceRead.model_validate(d) for d in query.order_by(Device.name).all()]


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
    return DeviceRead.model_validate(device)


def update_device(db: Session, device_id: str, payload: DeviceUpdate) -> DeviceRead | None:
    device = db.get(Device, device_id)
    if device is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    username = data.pop("username", None)
    password = data.pop("password", None)
    for key, value in data.items():
        setattr(device, key, value)
    if username is not None or password is not None:
        existing_user, existing_pass = decrypt_credentials(device.credentials_encrypted)
        device.credentials_encrypted = encrypt_credentials(
            username if username is not None else existing_user,
            password if password is not None else existing_pass,
        )
    db.commit()
    db.refresh(device)
    return DeviceRead.model_validate(device)


def delete_device(db: Session, device_id: str) -> bool:
    device = db.get(Device, device_id)
    if device is None:
        return False
    db.delete(device)
    db.commit()
    return True


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