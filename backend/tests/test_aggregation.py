from datetime import UTC, datetime

from app.db.session import SessionLocal
from app.models.device import Device, LatestStatus
from app.models.reachability import ExternalReachabilityResult
from app.services.aggregation import compute_high_level_summary


def test_aggregation_internet_degraded():
    db = SessionLocal()
    try:
        db.add(
            ExternalReachabilityResult(
                ipv4_ok=True,
                ipv6_ok=False,
                ipv4_targets=[],
                ipv6_targets=[],
                overall="degraded",
                timestamp=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
        summary = compute_high_level_summary(db)
        assert summary.banner == "internet_degraded"
    finally:
        db.close()


def test_aggregation_mixed():
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.important_flag.is_(True)).first()
        status = db.query(LatestStatus).filter(LatestStatus.device_id == device.id).first()
        status.overall = "down"
        db.add(
            ExternalReachabilityResult(
                ipv4_ok=True,
                ipv6_ok=False,
                ipv4_targets=[],
                ipv6_targets=[],
                overall="degraded",
                timestamp=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
        summary = compute_high_level_summary(db)
        assert summary.banner == "mixed"
    finally:
        db.close()