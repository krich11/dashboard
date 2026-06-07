from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.device import IssueItem, OperationalHistoryPoint
from app.services import status_history as status_history_service
from app.schemas.status import HighLevelSummary
from app.services.aggregation import compute_high_level_summary
from app.services.alert_service import evaluate_threshold_alerts, maybe_send_banner_alert
from app.services import devices as device_service

router = APIRouter(prefix="/api/v1/status", tags=["status"])


@router.get("/high-level", response_model=HighLevelSummary)
async def read_high_level_status(db: Session = Depends(get_db)) -> HighLevelSummary:
    summary = compute_high_level_summary(db)
    await maybe_send_banner_alert(db, summary)
    await evaluate_threshold_alerts(db, summary)
    return summary


@router.get("/issues", response_model=list[IssueItem])
def read_issues(
    important: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[IssueItem]:
    return device_service.list_issues(db, important_only=important)


@router.get("/history", response_model=list[OperationalHistoryPoint])
def read_operational_history(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=200, ge=1, le=1000),
    important: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[OperationalHistoryPoint]:
    return status_history_service.get_operational_history(
        db, hours=hours, limit=limit, important_only=important
    )