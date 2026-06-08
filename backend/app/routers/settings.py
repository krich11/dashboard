from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.config import get_settings
from app.schemas.alerts import AlertEventRead
from app.schemas.credentials import CredentialProfileWrite, CredentialProfilesResponse
from app.schemas.settings import (
    AlertSettings,
    AlertTestResult,
    CollectorRunResult,
    CollectorSettings,
    CollectorStatus,
    EncryptionStatus,
    EncryptionTestRequest,
    EncryptionTestResult,
    HistorySettings,
    MockScenarioSettings,
    ReachabilitySettings,
)
from app.services import reachability as reachability_service
from app.services.alert_service import (
    acknowledge_alert_event,
    get_alert_settings,
    list_alert_events,
    send_test_alert,
    update_alert_settings,
)
from app.services import credential_profiles_service, settings_service
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


@router.get("/history", response_model=HistorySettings)
def get_history_settings(db: Session = Depends(get_db)) -> HistorySettings:
    return settings_service.get_history_settings(db)


@router.put("/history", response_model=HistorySettings)
def update_history_settings(
    payload: HistorySettings, db: Session = Depends(get_db)
) -> HistorySettings:
    return settings_service.update_history_settings(db, payload)


@router.get("/collector/status", response_model=CollectorStatus)
def get_collector_status(db: Session = Depends(get_db)) -> CollectorStatus:
    return CollectorStatus(**collector_service.get_status(db))


@router.post("/collector/run", response_model=CollectorRunResult)
async def run_collector_once() -> CollectorRunResult:
    result = await collector_service.run_once()
    return CollectorRunResult(**result)


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


@router.get("/alerts", response_model=AlertSettings)
def read_alert_settings(db: Session = Depends(get_db)) -> AlertSettings:
    return get_alert_settings(db)


@router.put("/alerts", response_model=AlertSettings)
def write_alert_settings(payload: AlertSettings, db: Session = Depends(get_db)) -> AlertSettings:
    return update_alert_settings(db, payload)


@router.post("/alerts/test", response_model=AlertTestResult)
async def test_alert_webhook(db: Session = Depends(get_db)) -> AlertTestResult:
    return await send_test_alert(db)


@router.get("/alerts/events", response_model=list[AlertEventRead])
def read_alert_events(
    limit: int = 50,
    acknowledged: bool | None = None,
    db: Session = Depends(get_db),
) -> list[AlertEventRead]:
    return list_alert_events(db, limit=limit, acknowledged=acknowledged)


@router.post("/alerts/events/{event_id}/ack", response_model=AlertEventRead)
def ack_alert_event(event_id: int, db: Session = Depends(get_db)) -> AlertEventRead:
    event = acknowledge_alert_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Alert event not found")
    return event


@router.get("/encryption", response_model=EncryptionStatus)
def get_encryption_status() -> EncryptionStatus:
    return settings_service.get_encryption_status()


@router.post("/encryption/test", response_model=EncryptionTestResult)
def test_encryption(
    payload: EncryptionTestRequest, db: Session = Depends(get_db)
) -> EncryptionTestResult:
    return settings_service.test_encryption(db, payload)


@router.get("/credential-profiles", response_model=CredentialProfilesResponse)
def get_credential_profiles(db: Session = Depends(get_db)) -> CredentialProfilesResponse:
    return credential_profiles_service.get_credential_profiles(db)


@router.put("/credential-profiles", response_model=CredentialProfilesResponse)
def update_credential_profiles(
    payload: list[CredentialProfileWrite], db: Session = Depends(get_db)
) -> CredentialProfilesResponse:
    try:
        return credential_profiles_service.update_credential_profiles(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc