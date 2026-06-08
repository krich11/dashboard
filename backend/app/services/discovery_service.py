from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from app.collectors.factory import CONNECTOR_BY_TYPE, get_connector
from app.collectors.helpers import http_get_json, ping_host
from app.config import get_settings
from app.models.device import Device
from app.schemas.discovery import (
    CredentialTestResult,
    DiscoveryCandidate,
    DiscoveryImportResult,
    DiscoveryScanResult,
)
from app.schemas.device import DeviceCreate
from app.services import devices as device_service
from app.services.credential_profiles_service import (
    ResolvedCredential,
    get_resolved_profile_by_id,
    resolve_credentials_for_discovery,
)
from app.services.discovery_fingerprint import fingerprint_target, probe_ssh_login
from app.services.discovery_l2 import collect_l2_neighbors, neighbor_addresses
from app.services.discovery_targets import (
    build_default_target_hosts,
    expand_explicit_targets,
    get_default_scan_prefixes,
)

DEVICE_TYPES = tuple(CONNECTOR_BY_TYPE.keys())


def _max_scan_targets(requested: int | None = None) -> int:
    settings = get_settings()
    limit = requested or settings.discovery_max_targets
    return min(limit, settings.discovery_max_targets)


def resolve_scan_targets(
    targets: list[str] | None,
    *,
    use_default_ranges: bool,
    max_targets: int,
    rfc1918_only: bool,
    l2_addresses: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    hosts: list[str] = []
    prefixes: list[str] = []

    if use_default_ranges:
        default_hosts, prefixes = build_default_target_hosts(max_targets)
        hosts.extend(default_hosts)

    if targets:
        remaining = max_targets - len(hosts)
        if remaining > 0:
            hosts.extend(
                expand_explicit_targets(
                    targets,
                    max_targets=remaining,
                    rfc1918_only=rfc1918_only,
                )
            )

    if l2_addresses:
        seen = {h.lower() for h in hosts}
        for addr in l2_addresses:
            key = addr.lower()
            if key in seen:
                continue
            hosts.append(addr)
            seen.add(key)
            if len(hosts) >= max_targets:
                break

    if not hosts and not use_default_ranges:
        raise ValueError("Provide targets or enable use_default_ranges")

    if use_default_ranges and not prefixes:
        prefixes = get_default_scan_prefixes()

    return hosts[:max_targets], prefixes


async def probe_target(
    target: str,
    *,
    credential_attempts: list[ResolvedCredential],
    device_type_hint: str | None = None,
    discovery_source: str = "active_scan",
) -> DiscoveryCandidate:
    result = await fingerprint_target(
        target,
        device_type_hint=device_type_hint,
        credential_attempts=credential_attempts,
    )
    return DiscoveryCandidate(
        target=target,
        reachable=result["reachable"],
        detected_type=result.get("detected_type"),
        suggested_name=result.get("suggested_name"),
        suggested_hostname=result.get("suggested_hostname"),
        credentials_ok=result.get("credentials_ok"),
        message=result.get("message", ""),
        discovery_source=discovery_source,
        fingerprint_methods=result.get("fingerprint_methods", []),
        matched_credential_profile_id=result.get("matched_credential_profile_id"),
        matched_credential_profile_name=result.get("matched_credential_profile_name"),
    )


async def scan_network(
    db: Session | None,
    targets: list[str] | None = None,
    *,
    use_default_ranges: bool = True,
    infrastructure_device_ids: list[str] | None = None,
    include_arp_mac: bool = True,
    max_targets: int | None = None,
    rfc1918_only: bool = True,
    use_credential_profiles: bool = True,
    credential_profile_ids: list[str] | None = None,
    username: str | None = None,
    password: str | None = None,
    device_type_hint: str | None = None,
) -> DiscoveryScanResult:
    if device_type_hint and device_type_hint not in DEVICE_TYPES:
        raise ValueError(f"Unsupported device_type_hint. Choose one of: {', '.join(DEVICE_TYPES)}")

    limit = _max_scan_targets(max_targets)
    l2_neighbors_found = 0
    infrastructure_sources: list[str] = []
    l2_addresses: list[str] = []

    infra_attempts = resolve_credentials_for_discovery(
        db,
        profile_ids=credential_profile_ids,
        username=username,
        password=password,
        device_type=None,
        use_profiles=use_credential_profiles,
    ) if db is not None else []

    if include_arp_mac and db is not None and infrastructure_device_ids:
        neighbors, infrastructure_sources = await collect_l2_neighbors(
            db,
            infrastructure_device_ids,
            username=username,
            password=password,
            credential_attempts=infra_attempts,
        )
        l2_neighbors_found = len(neighbors)
        l2_addresses = neighbor_addresses(neighbors)

    hosts, prefixes = resolve_scan_targets(
        targets,
        use_default_ranges=use_default_ranges,
        max_targets=limit,
        rfc1918_only=rfc1918_only,
        l2_addresses=l2_addresses,
    )

    l2_set = {a.lower() for a in l2_addresses}

    async def scan_host(host: str) -> DiscoveryCandidate:
        attempts = resolve_credentials_for_discovery(
            db,
            profile_ids=credential_profile_ids,
            username=username,
            password=password,
            device_type=device_type_hint,
            use_profiles=use_credential_profiles,
        ) if db is not None else (
            [
                ResolvedCredential(
                    profile_id=None,
                    profile_name="manual",
                    username=username,
                    password=password,
                    device_types=(),
                )
            ]
            if username and password
            else []
        )
        return await probe_target(
            host,
            credential_attempts=attempts,
            device_type_hint=device_type_hint,
            discovery_source="arp_mac_table" if host.lower() in l2_set else "active_scan",
        )

    results = await asyncio.gather(*(scan_host(host) for host in hosts))
    detected_hosts = [candidate for candidate in results if candidate.reachable]
    return DiscoveryScanResult(
        scanned=len(hosts),
        candidates=detected_hosts,
        scan_prefixes=prefixes,
        l2_neighbors_found=l2_neighbors_found,
        infrastructure_sources=infrastructure_sources,
    )


async def test_device_credentials(
    db: Session,
    device_id: str,
    *,
    username: str | None = None,
    password: str | None = None,
) -> CredentialTestResult:
    device = device_service.get_device(db, device_id)
    if device is None:
        raise ValueError("Device not found")

    settings = get_settings()
    if settings.mock_mode:
        return CredentialTestResult(
            ok=True,
            message="Mock mode — credentials accepted",
            device_type=device.device_type,
            overall="ok",
        )

    if not device.connector_enabled:
        return CredentialTestResult(
            ok=False,
            message="Enable connector polling on this device before testing credentials",
            device_type=device.device_type,
        )

    from app.services.crypto import decrypt_credentials

    stored_user, stored_pass = decrypt_credentials(device.credentials_encrypted)
    user = username if username is not None else stored_user
    pwd = password if password is not None else stored_pass

    if device.device_type in {"hpe_ilorest", "juniper", "aruba"} and (not user or not pwd):
        return CredentialTestResult(
            ok=False,
            message="Username and password required for this connector",
            device_type=device.device_type,
        )

    target = device.management_ip or device.hostname
    try:
        if device.device_type == "hpe_ilorest":
            await http_get_json(f"https://{target}/redfish/v1/Systems/1", username=user, password=pwd)
            return CredentialTestResult(
                ok=True,
                message="Redfish authentication succeeded",
                device_type=device.device_type,
                overall="ok",
            )
        if device.device_type == "linux_ssh" and user and pwd:
            ok, msg, _ = await probe_ssh_login(target, user, pwd)
            return CredentialTestResult(
                ok=ok,
                message=msg,
                device_type=device.device_type,
                overall="ok" if ok else "down",
            )
        if device.device_type == "linux_ssh":
            reachable, _latency = await ping_host(target)
            return CredentialTestResult(
                ok=reachable,
                message="Ping reachable (no SSH credentials to test)"
                if reachable
                else "Host unreachable",
                device_type=device.device_type,
                overall="ok" if reachable else "down",
            )

        status = await get_connector(db, device).poll(device.id)
        return CredentialTestResult(
            ok=status.overall in {"ok", "warning"},
            message=status.message,
            device_type=device.device_type,
            overall=status.overall,
        )
    except Exception as exc:  # noqa: BLE001
        return CredentialTestResult(
            ok=False,
            message=str(exc),
            device_type=device.device_type,
            overall="down",
        )


def import_candidates(
    db: Session,
    candidates: list[DiscoveryCandidate],
    *,
    enable_connectors: bool = False,
    import_credentials: bool = False,
    username: str | None = None,
    password: str | None = None,
) -> DiscoveryImportResult:
    imported = 0
    skipped = 0
    existing_hosts = {
        (d.management_ip or d.hostname).lower()
        for d in db.query(Device).all()
    }

    for candidate in candidates:
        if not candidate.reachable or not candidate.detected_type:
            skipped += 1
            continue
        if candidate.target.lower() in existing_hosts:
            skipped += 1
            continue

        cred_user: str | None = None
        cred_pass: str | None = None
        if import_credentials:
            if candidate.matched_credential_profile_id:
                resolved = get_resolved_profile_by_id(db, candidate.matched_credential_profile_id)
                if resolved:
                    cred_user = resolved.username
                    cred_pass = resolved.password
            if (not cred_user or not cred_pass) and username and password:
                cred_user = username
                cred_pass = password

        has_creds = bool(cred_user and cred_pass)
        name = candidate.suggested_name or f"discovered-{candidate.target}"
        hostname = candidate.suggested_hostname or candidate.target
        payload = DeviceCreate(
            name=name,
            hostname=hostname,
            device_type=candidate.detected_type,
            management_ip=candidate.target,
            connector_enabled=enable_connectors and has_creds,
            username=cred_user if import_credentials and has_creds else None,
            password=cred_pass if import_credentials and has_creds else None,
        )
        device_service.create_device(db, payload)
        existing_hosts.add(candidate.target.lower())
        imported += 1

    return DiscoveryImportResult(imported=imported, skipped=skipped)