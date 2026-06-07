from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.device import Device, LatestStatus
from app.models.reachability import ExternalReachabilityResult
from app.models.settings import AppSettings
from app.schemas.settings import ReachabilitySettings
from app.services.dashboards import seed_default_dashboard
from app.services.mock_data import get_device_statuses, get_devices, get_reachability_latest
from app.services.status_history import record_device_status


def _parse_ts(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def seed_from_mocks(db: Session) -> None:
    if db.query(Device).count() > 0:
        return

    settings = get_settings()
    for item in get_devices():
        device = Device(
            id=item.id,
            name=item.name,
            hostname=item.hostname,
            device_type=item.device_type,
            tags=item.tags,
            important_flag=item.important_flag,
            management_ip=item.management_ip,
            connector_enabled=item.connector_enabled,
        )
        db.add(device)

    now = datetime.now(UTC).replace(tzinfo=None)
    for status in get_device_statuses(settings.mock_scenario):
        db.add(
            LatestStatus(
                device_id=status.device_id,
                overall=status.overall,
                message=status.message,
                metrics=status.metrics,
                details=status.details,
                timestamp=now,
            )
        )
        record_device_status(db, status.model_copy(update={"timestamp": now}), source="seed")

    reach = get_reachability_latest(settings.mock_scenario)
    db.add(
        ExternalReachabilityResult(
            ipv4_ok=reach.ipv4_ok,
            ipv6_ok=reach.ipv6_ok,
            ipv4_targets=[t.model_dump() for t in reach.ipv4_targets],
            ipv6_targets=[t.model_dump() for t in reach.ipv6_targets],
            overall=reach.overall,
            timestamp=now,
        )
    )

    reachability_settings = ReachabilitySettings(
        ipv4_targets=settings.reachability_ipv4_targets,
        ipv6_targets=settings.reachability_ipv6_targets,
        interval_sec=settings.reachability_interval_sec,
        timeout_sec=settings.reachability_timeout_sec,
        method=settings.reachability_method,  # type: ignore[arg-type]
        require_both_families=settings.reachability_require_both_families,
    )
    db.add(AppSettings(key="reachability", value=reachability_settings.model_dump()))
    db.commit()
    seed_default_dashboard(db)