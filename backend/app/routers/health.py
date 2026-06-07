from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.services.mock_scenario import get_active_mock_scenario

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    scenario = get_active_mock_scenario(db) if settings.mock_mode else settings.mock_scenario
    return {
        "status": "ok",
        "app": settings.app_name,
        "mock_mode": settings.mock_mode,
        "mock_scenario": scenario,
    }