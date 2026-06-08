from app.config import get_settings
from app.db.session import SessionLocal
from app.models.device import Device, LatestStatus
from app.models.reachability import ExternalReachabilityResult
from app.models.settings import AppSettings
from app.services.seed import seed_from_mocks


def test_seed_from_mocks_is_idempotent():
    db = SessionLocal()
    try:
        before_devices = db.query(Device).count()
        before_settings = db.get(AppSettings, "reachability") is not None
        seed_from_mocks(db)
        assert db.query(Device).count() == before_devices
        assert (db.get(AppSettings, "reachability") is not None) == before_settings
    finally:
        db.close()


def test_seed_with_existing_reachability_and_no_devices():
    db = SessionLocal()
    try:
        db.query(Device).delete()
        db.query(LatestStatus).delete()
        db.query(ExternalReachabilityResult).delete()
        db.commit()
        assert db.query(Device).count() == 0
        assert db.get(AppSettings, "reachability") is not None
        seed_from_mocks(db)
    finally:
        db.close()


def test_seed_skips_mock_devices_when_mock_mode_disabled(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    get_settings.cache_clear()
    db = SessionLocal()
    try:
        db.query(Device).delete()
        db.commit()
        seed_from_mocks(db)
        assert db.query(Device).count() == 0
    finally:
        db.close()
        get_settings.cache_clear()