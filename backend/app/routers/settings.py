from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.settings import (
    CollectorSettings,
    CollectorStatus,
    EncryptionStatus,
    EncryptionTestRequest,
    EncryptionTestResult,
    ReachabilitySettings,
)
from app.services import reachability as reachability_service
from app.services import settings_service
from app.services.collector_service import collector_service

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("/reachability", response_model=ReachabilitySettings)
def get_reachability_settings(db: Session = Depends(get_db)) -> ReachabilitySettings:
    return reachability_service.get_reachability_settings(db)


@router.put("/reachability", response_model=ReachabilitySettings)
def update_reachability_settings(
    payload: ReachabilitySettings, db: Session = Depends(get_db)
) -> ReachabilitySettings:
    return reachability_service.update_reachability_settings(db, payload)


@router.get("/collector", response_model=CollectorSettings)
def get_collector_settings(db: Session = Depends(get_db)) -> CollectorSettings:
    return settings_service.get_collector_settings(db)


@router.put("/collector", response_model=CollectorSettings)
def update_collector_settings(
    payload: CollectorSettings, db: Session = Depends(get_db)
) -> CollectorSettings:
    return settings_service.update_collector_settings(db, payload)


@router.get("/collector/status", response_model=CollectorStatus)
def get_collector_status(db: Session = Depends(get_db)) -> CollectorStatus:
    return CollectorStatus(**collector_service.get_status(db))


@router.get("/encryption", response_model=EncryptionStatus)
def get_encryption_status() -> EncryptionStatus:
    return settings_service.get_encryption_status()


@router.post("/encryption/test", response_model=EncryptionTestResult)
def test_encryption(
    payload: EncryptionTestRequest, db: Session = Depends(get_db)
) -> EncryptionTestResult:
    return settings_service.test_encryption(db, payload)