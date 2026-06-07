from sqlalchemy.orm import Session

from app.models.reachability import ExternalReachabilityResult
from app.models.settings import AppSettings
from app.schemas.reachability import ExternalReachabilityRead, ReachabilityTargetResult
from app.schemas.settings import ReachabilitySettings


def get_latest_reachability(db: Session) -> ExternalReachabilityRead | None:
    row = (
        db.query(ExternalReachabilityResult)
        .order_by(ExternalReachabilityResult.timestamp.desc())
        .first()
    )
    if row is None:
        return None
    return ExternalReachabilityRead(
        ipv4_ok=row.ipv4_ok,
        ipv6_ok=row.ipv6_ok,
        ipv4_targets=[ReachabilityTargetResult(**t) for t in row.ipv4_targets],
        ipv6_targets=[ReachabilityTargetResult(**t) for t in row.ipv6_targets],
        overall=row.overall,
        timestamp=row.timestamp,
    )


def get_reachability_settings(db: Session) -> ReachabilitySettings:
    row = db.get(AppSettings, "reachability")
    if row and row.value:
        return ReachabilitySettings(**row.value)
    from app.config import get_settings

    s = get_settings()
    return ReachabilitySettings(
        ipv4_targets=s.reachability_ipv4_targets,
        ipv6_targets=s.reachability_ipv6_targets,
        interval_sec=s.reachability_interval_sec,
        timeout_sec=s.reachability_timeout_sec,
        method=s.reachability_method,  # type: ignore[arg-type]
        require_both_families=s.reachability_require_both_families,
    )


def update_reachability_settings(db: Session, payload: ReachabilitySettings) -> ReachabilitySettings:
    row = db.get(AppSettings, "reachability")
    if row is None:
        row = AppSettings(key="reachability", value=payload.model_dump())
        db.add(row)
    else:
        row.value = payload.model_dump()
    db.commit()
    return payload