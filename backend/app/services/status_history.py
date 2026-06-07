from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.device import Device
from app.services.settings_service import get_history_settings
from app.models.status_history import DeviceStatusHistory
from app.schemas.device import DeviceStatusHistoryPoint, DeviceStatusRead, OperationalHistoryPoint

SEVERITY = {"ok": 0, "warning": 1, "degraded": 1, "critical": 2, "down": 3, "unknown": 1}


def _naive_utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hour_start(ts: datetime) -> datetime:
    return ts.replace(minute=0, second=0, microsecond=0)


def _day_start(ts: datetime) -> datetime:
    return ts.replace(hour=0, minute=0, second=0, microsecond=0)


def record_device_status(
    db: Session,
    status: DeviceStatusRead,
    *,
    source: str = "collector",
) -> None:
    ts = status.timestamp.replace(tzinfo=None) if status.timestamp.tzinfo else status.timestamp
    db.add(
        DeviceStatusHistory(
            device_id=status.device_id,
            overall=status.overall,
            message=status.message,
            metrics=status.metrics,
            details=status.details,
            timestamp=ts,
            source=source,
            granularity="raw",
        )
    )


def get_device_status_history(
    db: Session,
    device_id: str,
    *,
    hours: int = 24,
    limit: int = 500,
) -> list[DeviceStatusHistoryPoint]:
    since = _naive_utc_now() - timedelta(hours=hours)
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
    return [_to_history_point(row) for row in rows]


def get_operational_history(
    db: Session,
    *,
    hours: int = 24,
    limit: int = 200,
    important_only: bool = True,
) -> list[OperationalHistoryPoint]:
    since = _naive_utc_now() - timedelta(hours=hours)
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
    buckets: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        epoch = int(row.timestamp.timestamp())
        key = epoch - (epoch % bucket_seconds)
        buckets[key].append(row.overall)

    points: list[OperationalHistoryPoint] = []
    for key in sorted(buckets.keys()):
        statuses = buckets[key]
        down = sum(1 for s in statuses if s in {"down", "critical"})
        up = sum(1 for s in statuses if s == "ok")
        worst = max(statuses, key=lambda s: SEVERITY.get(s, 1))
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


def _to_history_point(row: DeviceStatusHistory) -> DeviceStatusHistoryPoint:
    return DeviceStatusHistoryPoint(
        device_id=row.device_id,
        overall=row.overall,
        message=row.message,
        timestamp=row.timestamp,
        source=row.source,
        granularity=row.granularity,
    )


def _pick_worst(rows: list[DeviceStatusHistory]) -> DeviceStatusHistory:
    return max(rows, key=lambda row: SEVERITY.get(row.overall, 1))


def _upsert_summary(
    db: Session,
    *,
    device_id: str,
    timestamp: datetime,
    granularity: str,
    template: DeviceStatusHistory,
) -> None:
    existing = (
        db.query(DeviceStatusHistory)
        .filter(
            DeviceStatusHistory.device_id == device_id,
            DeviceStatusHistory.granularity == granularity,
            DeviceStatusHistory.timestamp == timestamp,
        )
        .first()
    )
    if existing:
        if SEVERITY.get(template.overall, 1) > SEVERITY.get(existing.overall, 1):
            existing.overall = template.overall
            existing.message = template.message
            existing.metrics = template.metrics
            existing.details = template.details
            existing.source = "rollup"
        return

    db.add(
        DeviceStatusHistory(
            device_id=device_id,
            overall=template.overall,
            message=template.message,
            metrics=template.metrics,
            details=template.details,
            timestamp=timestamp,
            source="rollup",
            granularity=granularity,
        )
    )


def _summarize_tier(
    db: Session,
    *,
    source_granularity: str,
    target_granularity: str,
    bucket_fn,
    older_than: datetime,
) -> int:
    rows = (
        db.query(DeviceStatusHistory)
        .filter(
            DeviceStatusHistory.granularity == source_granularity,
            DeviceStatusHistory.timestamp < older_than,
        )
        .all()
    )
    if not rows:
        return 0

    grouped: dict[tuple[str, datetime], list[DeviceStatusHistory]] = defaultdict(list)
    for row in rows:
        grouped[(row.device_id, bucket_fn(row.timestamp))].append(row)

    for (device_id, bucket_ts), group in grouped.items():
        worst = _pick_worst(group)
        _upsert_summary(
            db,
            device_id=device_id,
            timestamp=bucket_ts,
            granularity=target_granularity,
            template=worst,
        )

    source_ids = [row.id for row in rows]
    db.query(DeviceStatusHistory).filter(DeviceStatusHistory.id.in_(source_ids)).delete(
        synchronize_session=False
    )
    return len(source_ids)


def prune_status_history(db: Session) -> int:
    """Roll up aged raw→hourly and hourly→daily tiers. Daily rows are kept forever."""
    history = get_history_settings(db)
    now = _naive_utc_now()
    raw_cutoff = now - timedelta(days=history.raw_days)
    hourly_cutoff = now - timedelta(days=history.hourly_days)

    summarized = 0
    summarized += _summarize_tier(
        db,
        source_granularity="raw",
        target_granularity="hourly",
        bucket_fn=_hour_start,
        older_than=raw_cutoff,
    )
    summarized += _summarize_tier(
        db,
        source_granularity="hourly",
        target_granularity="daily",
        bucket_fn=_day_start,
        older_than=hourly_cutoff,
    )
    db.commit()
    return summarized