from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.reachability import ExternalReachabilityRead, ReachabilityHistoryPoint
from app.services import reachability as reachability_service

router = APIRouter(prefix="/api/v1/reachability", tags=["reachability"])


@router.get("/latest", response_model=ExternalReachabilityRead)
def read_reachability_latest(db: Session = Depends(get_db)) -> ExternalReachabilityRead:
    result = reachability_service.get_latest_reachability(db)
    if result is None:
        raise HTTPException(status_code=404, detail="No reachability data yet")
    return result


@router.get("/history", response_model=list[ReachabilityHistoryPoint])
def read_reachability_history(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ReachabilityHistoryPoint]:
    return reachability_service.get_reachability_history(db, hours=hours, limit=limit)