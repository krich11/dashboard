from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.settings import ReachabilitySettings
from app.services import reachability as reachability_service

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("/reachability", response_model=ReachabilitySettings)
def get_reachability_settings(db: Session = Depends(get_db)) -> ReachabilitySettings:
    return reachability_service.get_reachability_settings(db)


@router.put("/reachability", response_model=ReachabilitySettings)
def update_reachability_settings(
    payload: ReachabilitySettings, db: Session = Depends(get_db)
) -> ReachabilitySettings:
    return reachability_service.update_reachability_settings(db, payload)