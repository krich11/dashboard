from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.config import get_settings
from app.schemas.settings import (
    CollectorSettings,
    CollectorStatus,
    EncryptionStatus,
    EncryptionTestRequest,
    EncryptionTestResult,
    MockScenarioSettings,
    ReachabilitySettings,
)
from app.services import reachability as reachability_service
from app.services import settings_service
from app.services.collector_service import collector_service
from app.services.mock_scenario import VALID_SCENARIOS, get_active_mock_scenario, set_mock_scenario

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


@router.get("/mock-scenario", response_model=MockScenarioSettings)
def get_mock_scenario_settings(db: Session = Depends(get_db)) -> MockScenarioSettings:
    if not get_settings().mock_mode:
        raise HTTPException(status_code=400, detail="Mock scenario API only available in MOCK_MODE")
    return MockScenarioSettings(
        scenario=get_active_mock_scenario(db),
        available=list(VALID_SCENARIOS),
    )


@router.put("/mock-scenario", response_model=MockScenarioSettings)
def update_mock_scenario_settings(
    payload: MockScenarioSettings, db: Session = Depends(get_db)
) -> MockScenarioSettings:
    if not get_settings().mock_mode:
        raise HTTPException(status_code=400, detail="Mock scenario API only available in MOCK_MODE")
    try:
        scenario = set_mock_scenario(db, payload.scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MockScenarioSettings(scenario=scenario, available=list(VALID_SCENARIOS))


@router.get("/encryption", response_model=EncryptionStatus)
def get_encryption_status() -> EncryptionStatus:
    return settings_service.get_encryption_status()


@router.post("/encryption/test", response_model=EncryptionTestResult)
def test_encryption(
    payload: EncryptionTestRequest, db: Session = Depends(get_db)
) -> EncryptionTestResult:
    return settings_service.test_encryption(db, payload)