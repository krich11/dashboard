from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.discovery import (
    DiscoveryImportRequest,
    DiscoveryImportResult,
    DiscoveryPrefixesResult,
    DiscoveryScanRequest,
    DiscoveryScanResult,
)
from app.services import discovery_service
from app.services.discovery_targets import get_default_scan_prefixes

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


@router.get("/prefixes", response_model=DiscoveryPrefixesResult)
def list_discovery_prefixes() -> DiscoveryPrefixesResult:
    return DiscoveryPrefixesResult(prefixes=get_default_scan_prefixes())


@router.post("/scan", response_model=DiscoveryScanResult)
async def scan_discovery(
    payload: DiscoveryScanRequest, db: Session = Depends(get_db)
) -> DiscoveryScanResult:
    try:
        return await discovery_service.scan_network(
            db,
            payload.targets or None,
            use_default_ranges=payload.use_default_ranges,
            infrastructure_device_ids=payload.infrastructure_device_ids or None,
            include_arp_mac=payload.include_arp_mac,
            max_targets=payload.max_targets,
            rfc1918_only=payload.rfc1918_only,
            use_credential_profiles=payload.use_credential_profiles,
            credential_profile_ids=payload.credential_profile_ids or None,
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