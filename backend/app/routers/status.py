from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.device import IssueItem
from app.schemas.status import HighLevelSummary
from app.services.aggregation import compute_high_level_summary
from app.services import devices as device_service

router = APIRouter(prefix="/api/v1/status", tags=["status"])


@router.get("/high-level", response_model=HighLevelSummary)
def read_high_level_status(db: Session = Depends(get_db)) -> HighLevelSummary:
    return compute_high_level_summary(db)


@router.get("/issues", response_model=list[IssueItem])
def read_issues(
    important: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[IssueItem]:
    return device_service.list_issues(db, important_only=important)