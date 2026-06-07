from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.discovery import (
    CredentialTestRequest,
    CredentialTestResult,
    DiscoveryImportRequest,
    DiscoveryImportResult,
    DiscoveryScanRequest,
    DiscoveryScanResult,
)
from app.services import discovery_service

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


@router.post("/scan", response_model=DiscoveryScanResult)
async def scan_discovery(payload: DiscoveryScanRequest) -> DiscoveryScanResult:
    try:
        return await discovery_service.scan_network(
            payload.targets,
            username=payload.username,
            password=payload.password,
            device_type_hint=payload.device_type_hint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import", response_model=DiscoveryImportResult)
def import_discovery(
    payload: DiscoveryImportRequest, db: Session = Depends(get_db)
) -> DiscoveryImportResult:
    return discovery_service.import_candidates(
        db,
        payload.candidates,
        enable_connectors=payload.enable_connectors,
        import_credentials=payload.import_credentials,
        username=payload.username,
        password=payload.password,
    )