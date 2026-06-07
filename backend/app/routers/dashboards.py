from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardCreate, DashboardRead, DashboardUpdate
from app.services import dashboards as dashboard_service

router = APIRouter(prefix="/api/v1/dashboards", tags=["dashboards"])


@router.get("", response_model=list[DashboardRead])
def list_dashboards(db: Session = Depends(get_db)) -> list[DashboardRead]:
    return dashboard_service.list_dashboards(db)


@router.get("/default", response_model=DashboardRead)
def get_default_dashboard(db: Session = Depends(get_db)) -> DashboardRead:
    dashboard = dashboard_service.get_default_dashboard(db)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="No default dashboard")
    return dashboard


@router.get("/{dashboard_id}", response_model=DashboardRead)
def get_dashboard(dashboard_id: str, db: Session = Depends(get_db)) -> DashboardRead:
    dashboard = dashboard_service.get_dashboard(db, dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard


@router.post("", response_model=DashboardRead, status_code=201)
def create_dashboard(payload: DashboardCreate, db: Session = Depends(get_db)) -> DashboardRead:
    return dashboard_service.create_dashboard(db, payload)


@router.put("/{dashboard_id}", response_model=DashboardRead)
def update_dashboard(
    dashboard_id: str, payload: DashboardUpdate, db: Session = Depends(get_db)
) -> DashboardRead:
    dashboard = dashboard_service.update_dashboard(db, dashboard_id, payload)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard