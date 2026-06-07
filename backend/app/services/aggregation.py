from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models.device import Device, LatestStatus
from app.models.reachability import ExternalReachabilityResult
from app.schemas.status import HighLevelSummary
from app.services.normalization import is_device_up
from app.services.settings_service import get_collector_settings


def _internet_health(reach: ExternalReachabilityResult | None, require_both: bool) -> str:
    if reach is None:
        return "unknown"
    if require_both:
        if reach.ipv4_ok and reach.ipv6_ok:
            return "ok"
        if reach.ipv4_ok or reach.ipv6_ok:
            return "degraded"
        return "down"
    return "ok" if (reach.ipv4_ok or reach.ipv6_ok) else "down"


def _internet_summary(reach: ExternalReachabilityResult | None) -> str:
    if reach is None:
        return "No reachability data"
    ipv4 = "OK" if reach.ipv4_ok else "Down"
    ipv6 = "OK" if reach.ipv6_ok else "Degraded" if not reach.ipv6_ok and reach.ipv4_ok else "Down"
    return f"IPv4 {ipv4}, IPv6 {ipv6}"


def compute_high_level_summary(db: Session) -> HighLevelSummary:
    settings = get_settings()
    collector = get_collector_settings(db)
    devices = (
        db.query(Device)
        .options(joinedload(Device.latest_status))
        .filter(Device.important_flag.is_(True))
        .all()
    )
    reach = (
        db.query(ExternalReachabilityResult)
        .order_by(ExternalReachabilityResult.timestamp.desc())
        .first()
    )
    require_both = settings.reachability_require_both_families
    internet_health = _internet_health(reach, require_both)

    important_down = 0
    for device in devices:
        status: LatestStatus | None = device.latest_status
        if status is None or not is_device_up(
            status.overall, status.timestamp, collector.status_staleness_sec
        ):
            important_down += 1
    important_total = len(devices)
    important_up = important_total - important_down

    if important_down > 0 and internet_health != "ok":
        banner = "mixed"
        banner_text = f"{important_down} Important Devices Down; Internet Degraded"
        worst = "critical"
    elif important_down > 0:
        banner = "devices_down"
        banner_text = f"{important_down} Important Devices Down"
        worst = "critical"
    elif internet_health != "ok":
        banner = "internet_degraded"
        banner_text = "Internet Degraded"
        worst = "warning"
    else:
        banner = "all_clear"
        banner_text = "All Systems Operational"
        worst = "ok"

    return HighLevelSummary(
        banner=banner,
        banner_text=banner_text,
        important_total=important_total,
        important_up=important_up,
        important_down=important_down,
        internet_health=internet_health,
        internet_summary=_internet_summary(reach),
        worst_overall=worst,
        timestamp=datetime.now(UTC),
    )