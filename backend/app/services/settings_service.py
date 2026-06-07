from app.config import get_settings
from app.models.settings import AppSettings
from app.schemas.settings import (
    CollectorSettings,
    EncryptionStatus,
    EncryptionTestRequest,
    EncryptionTestResult,
    HistorySettings,
)
from app.services.crypto import CredentialCipher
from sqlalchemy.orm import Session

DEV_DEFAULT_KEY = "dev-only-change-in-production"


def _get_or_default(db: Session, key: str, defaults: dict) -> dict:
    row = db.get(AppSettings, key)
    if row and row.value:
        return {**defaults, **row.value}
    return defaults


def get_collector_settings(db: Session) -> CollectorSettings:
    settings = get_settings()
    defaults = {
        "interval_sec": settings.collector_interval_sec,
        "concurrency": settings.collector_concurrency,
        "default_backoff_sec": settings.collector_default_backoff_sec,
        "max_backoff_sec": settings.collector_max_backoff_sec,
        "circuit_breaker_threshold": settings.collector_circuit_breaker_threshold,
        "status_staleness_sec": settings.status_staleness_sec,
    }
    return CollectorSettings(**_get_or_default(db, "collector", defaults))


def get_history_settings(db: Session) -> HistorySettings:
    settings = get_settings()
    defaults = {
        "raw_days": settings.status_history_raw_days,
        "hourly_days": settings.status_history_hourly_days,
    }
    return HistorySettings(**_get_or_default(db, "history", defaults))


def update_history_settings(db: Session, payload: HistorySettings) -> HistorySettings:
    row = db.get(AppSettings, "history")
    if row is None:
        row = AppSettings(key="history", value=payload.model_dump())
        db.add(row)
    else:
        row.value = payload.model_dump()
    db.commit()
    return payload


def update_collector_settings(db: Session, payload: CollectorSettings) -> CollectorSettings:
    row = db.get(AppSettings, "collector")
    if row is None:
        row = AppSettings(key="collector", value=payload.model_dump())
        db.add(row)
    else:
        row.value = payload.model_dump()
    db.commit()
    return payload


def get_encryption_status() -> EncryptionStatus:
    settings = get_settings()
    key = settings.dashboard_secret_key
    is_dev = key == DEV_DEFAULT_KEY
    if not key:
        return EncryptionStatus(
            configured=False,
            is_dev_default=True,
            message="DASHBOARD_SECRET_KEY is not set. Device credentials cannot be encrypted.",
        )
    if is_dev:
        return EncryptionStatus(
            configured=True,
            is_dev_default=True,
            message="Using development default key. Set DASHBOARD_SECRET_KEY in production.",
        )
    return EncryptionStatus(
        configured=True,
        is_dev_default=False,
        message="Encryption key configured via environment.",
    )


def test_encryption(_: Session, payload: EncryptionTestRequest) -> EncryptionTestResult:
    try:
        cipher = CredentialCipher()
        encrypted = cipher.encrypt(payload.test_value)
        decrypted = cipher.decrypt(encrypted)
        if decrypted != payload.test_value:
            return EncryptionTestResult(ok=False, message="Round-trip mismatch")
        return EncryptionTestResult(ok=True, message="Encryption round-trip succeeded")
    except ValueError as exc:
        return EncryptionTestResult(ok=False, message=str(exc))