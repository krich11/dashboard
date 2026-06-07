from fastapi import APIRouter, Query

from app.schemas.reachability import ExternalReachabilityRead
from app.services.mock_data import get_reachability_latest

router = APIRouter(prefix="/api/v1/reachability", tags=["reachability"])


@router.get("/latest", response_model=ExternalReachabilityRead)
def read_reachability_latest(
    scenario: str | None = Query(default=None, description="Mock scenario override"),
) -> ExternalReachabilityRead:
    return get_reachability_latest(scenario)