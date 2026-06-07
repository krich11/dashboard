from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.device import Device
from app.models.status_history import DeviceStatusHistory
from app.schemas.device import DeviceStatusHistoryPoint, DeviceStatusRead, OperationalHistoryPoint


def record_device_status(
    db: Session,
    status: DeviceStatusRead,
    *,
    source: str = "collector",
) -> None:
    db.add(
        DeviceStatusHistory(
            device_id=status.device_id,
            overall=status.overall,
            message=status.message,
            metrics=status.metrics,
            details=status.details,
            timestamp=status.timestamp.replace(tzinfo=None)
            if status.timestamp.tzinfo
            else status.timestamp,
            source=source,
        )
    )


def get_device_status_history(
    db: Session,
    device_id: str,
    *,
    hours: int = 24,
    limit: int = 500,
) -> list[DeviceStatusHistoryPoint]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)
    rows = (
        db.query(DeviceStatusHistory)
        .filter(
            DeviceStatusHistory.device_id == device_id,
            DeviceStatusHistory.timestamp >= since,
        )
        .order_by(DeviceStatusHistory.timestamp.asc())
        .limit(limit)
        .all()
    )
    return [
        DeviceStatusHistoryPoint(
            device_id=row.device_id,
            overall=row.overall,
            message=row.message,
            timestamp=row.timestamp,
            source=row.source,
        )
        for row in rows
    ]


def get_operational_history(
    db: Session,
    *,
    hours: int = 24,
    limit: int = 200,
    important_only: bool = True,
) -> list[OperationalHistoryPoint]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)
    query = db.query(DeviceStatusHistory).filter(DeviceStatusHistory.timestamp >= since)
    if important_only:
        important_ids = [
            d.id for d in db.query(Device).filter(Device.important_flag.is_(True)).all()
        ]
        if not important_ids:
            return []
        query = query.filter(DeviceStatusHistory.device_id.in_(important_ids))

    rows = query.order_by(DeviceStatusHistory.timestamp.asc()).all()
    if not rows:
        return []

    bucket_seconds = 300
    buckets: dict[int, list[str]] = {}
    for row in rows:
        epoch = int(row.timestamp.timestamp())
        key = epoch - (epoch % bucket_seconds)
        buckets.setdefault(key, []).append(row.overall)

    severity = {"ok": 0, "warning": 1, "degraded": 1, "critical": 2, "down": 3, "unknown": 1}

    points: list[OperationalHistoryPoint] = []
    for key in sorted(buckets.keys()):
        statuses = buckets[key]
        down = sum(1 for s in statuses if s in {"down", "critical"})
        up = sum(1 for s in statuses if s == "ok")
        worst = max(statuses, key=lambda s: severity.get(s, 1))
        points.append(
            OperationalHistoryPoint(
                timestamp=datetime.fromtimestamp(key, tz=UTC).replace(tzinfo=None),
                important_total=len(statuses),
                important_up=up,
                important_down=down,
                worst_overall=worst,
            )
        )

    return points[-limit:]


def prune_status_history(db: Session) -> int:
    settings = get_settings()
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
        days=settings.status_history_retention_days
    )
    deleted = (
        db.query(DeviceStatusHistory)
        .filter(DeviceStatusHistory.timestamp < cutoff)
        .delete(synchronize_session=False)
    )

    max_per_device = settings.status_history_max_per_device
    device_ids = [row[0] for row in db.query(DeviceStatusHistory.device_id).distinct().all()]
    for device_id in device_ids:
        count = (
            db.query(func.count(DeviceStatusHistory.id))
            .filter(DeviceStatusHistory.device_id == device_id)
            .scalar()
            or 0
        )
        if count <= max_per_device:
            continue
        excess = count - max_per_device
        oldest_ids = [
            row[0]
            for row in (
                db.query(DeviceStatusHistory.id)
                .filter(DeviceStatusHistory.device_id == device_id)
                .order_by(DeviceStatusHistory.timestamp.asc())
                .limit(excess)
                .all()
            )
        ]
        if oldest_ids:
            db.query(DeviceStatusHistory).filter(DeviceStatusHistory.id.in_(oldest_ids)).delete(
                synchronize_session=False
            )
            deleted += len(oldest_ids)

    db.commit()
    return deleted