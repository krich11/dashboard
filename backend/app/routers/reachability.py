from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.reachability import ExternalReachabilityRead
from app.schemas.settings import ReachabilitySettings
from app.services import reachability as reachability_service

router = APIRouter(prefix="/api/v1/reachability", tags=["reachability"])


@router.get("/latest", response_model=ExternalReachabilityRead)
def read_reachability_latest(db: Session = Depends(get_db)) -> ExternalReachabilityRead:
    result = reachability_service.get_latest_reachability(db)
    if result is None:
        raise HTTPException(status_code=404, detail="No reachability data yet")
    return result