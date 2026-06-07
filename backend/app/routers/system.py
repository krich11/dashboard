from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.services.collector_service import collector_service
from app.services.mock_scenario import get_active_mock_scenario
from app.services import settings_service

router = APIRouter(prefix="/api/v1/system", tags=["system"])

APP_VERSION = "1.5.2"


@router.get("/info")
def system_info(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    collector = collector_service.get_status(db)
    return {
        "app": settings.app_name,
        "version": APP_VERSION,
        "mock_mode": settings.mock_mode,
        "mock_scenario": get_active_mock_scenario(db) if settings.mock_mode else None,
        "collector_running": collector["running"],
        "total_devices": collector["total_devices"],
        "history_raw_days": settings_service.get_history_settings(db).raw_days,
        "history_hourly_days": settings_service.get_history_settings(db).hourly_days,
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }