from fastapi import APIRouter, Query

from app.schemas.status import HighLevelSummary
from app.services.mock_data import get_high_level_summary

router = APIRouter(prefix="/api/v1/status", tags=["status"])


@router.get("/high-level", response_model=HighLevelSummary)
def read_high_level_status(
    scenario: str | None = Query(default=None, description="Mock scenario override"),
) -> HighLevelSummary:
    return get_high_level_summary(scenario)