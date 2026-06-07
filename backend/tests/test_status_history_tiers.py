from datetime import UTC, datetime, timedelta

from app.db.session import SessionLocal
from app.models.device import Device
from app.models.status_history import DeviceStatusHistory
from app.services.status_history import prune_status_history


def test_raw_rolls_up_to_hourly_after_threshold():
    db = SessionLocal()
    try:
        device_id = db.query(Device).first().id
        old_ts = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=31)
        db.add(
            DeviceStatusHistory(
                device_id=device_id,
                overall="ok",
                message="old raw",
                metrics={},
                details={},
                timestamp=old_ts,
                source="collector",
                granularity="raw",
            )
        )
        db.commit()

        summarized = prune_status_history(db)
        assert summarized >= 1

        aged_raw = (
            db.query(DeviceStatusHistory)
            .filter(
                DeviceStatusHistory.device_id == device_id,
                DeviceStatusHistory.granularity == "raw",
                DeviceStatusHistory.timestamp < old_ts + timedelta(hours=1),
            )
            .count()
        )
        hourly = (
            db.query(DeviceStatusHistory)
            .filter(
                DeviceStatusHistory.device_id == device_id,
                DeviceStatusHistory.granularity == "hourly",
            )
            .all()
        )
        assert aged_raw == 0
        assert len(hourly) == 1
        assert hourly[0].timestamp == old_ts.replace(minute=0, second=0, microsecond=0)
    finally:
        db.close()


def test_hourly_rolls_up_to_daily_and_daily_is_kept():
    db = SessionLocal()
    try:
        device_id = db.query(Device).order_by(Device.name.desc()).first().id
        old_ts = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=95)
        db.add(
            DeviceStatusHistory(
                device_id=device_id,
                overall="critical",
                message="old hourly",
                metrics={},
                details={},
                timestamp=old_ts,
                source="rollup",
                granularity="hourly",
            )
        )
        db.commit()

        summarized = prune_status_history(db)
        assert summarized == 1

        daily = (
            db.query(DeviceStatusHistory)
            .filter(
                DeviceStatusHistory.device_id == device_id,
                DeviceStatusHistory.granularity == "daily",
            )
            .all()
        )
        assert len(daily) == 1
        assert daily[0].overall == "critical"
        assert daily[0].timestamp == old_ts.replace(hour=0, minute=0, second=0, microsecond=0)

        prune_status_history(db)
        still_daily = (
            db.query(DeviceStatusHistory)
            .filter(
                DeviceStatusHistory.device_id == device_id,
                DeviceStatusHistory.granularity == "daily",
            )
            .count()
        )
        assert still_daily == 1
    finally:
        db.close()