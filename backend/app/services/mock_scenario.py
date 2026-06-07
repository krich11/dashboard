import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import ROOT_DIR, get_settings
from app.models.device import LatestStatus
from app.models.reachability import ExternalReachabilityResult
from app.models.settings import AppSettings
from app.services.mock_data import get_device_statuses, get_reachability_latest

VALID_SCENARIOS = tuple(json.loads((ROOT_DIR / "mocks" / "scenarios.json").read_text()).keys())


def get_active_mock_scenario(db: Session) -> str:
    row = db.get(AppSettings, "mock")
    if row and row.value.get("scenario") in VALID_SCENARIOS:
        return row.value["scenario"]
    return get_settings().mock_scenario


def set_mock_scenario(db: Session, scenario: str) -> str:
    if scenario not in VALID_SCENARIOS:
        raise ValueError(f"Invalid scenario. Choose one of: {', '.join(VALID_SCENARIOS)}")
    row = db.get(AppSettings, "mock")
    if row is None:
        row = AppSettings(key="mock", value={"scenario": scenario})
        db.add(row)
    else:
        row.value = {"scenario": scenario}
    apply_mock_scenario_to_db(db, scenario)
    db.commit()
    db.expire_all()
    return scenario


def apply_mock_scenario_to_db(db: Session, scenario: str) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    for status in get_device_statuses(scenario):
        existing = db.query(LatestStatus).filter(LatestStatus.device_id == status.device_id).first()
        if existing:
            existing.overall = status.overall
            existing.message = status.message
            existing.metrics = status.metrics
            existing.details = status.details
            existing.timestamp = now
        else:
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

    reach = get_reachability_latest(scenario)
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