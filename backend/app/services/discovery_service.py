from __future__ import annotations

import asyncio
import ipaddress
from sqlalchemy.orm import Session

from app.config import get_settings
from app.collectors.helpers import ConnectorError, http_get_json, ping_host
from app.models.device import Device
from app.schemas.discovery import (
    CredentialTestResult,
    DiscoveryCandidate,
    DiscoveryImportResult,
    DiscoveryScanResult,
)
from app.schemas.device import DeviceCreate
from app.services import devices as device_service
from app.collectors.factory import CONNECTOR_BY_TYPE, get_connector

MAX_SCAN_TARGETS = 256
DEVICE_TYPES = tuple(CONNECTOR_BY_TYPE.keys())


def expand_targets(targets: list[str]) -> list[str]:
    expanded: list[str] = []
    for raw in targets:
        value = raw.strip()
        if not value:
            continue
        if "/" in value:
            network = ipaddress.ip_network(value, strict=False)
            for host in network.hosts():
                expanded.append(str(host))
                if len(expanded) >= MAX_SCAN_TARGETS:
                    return expanded
        else:
            expanded.append(value)
            if len(expanded) >= MAX_SCAN_TARGETS:
                return expanded
    return expanded


async def _port_open(target: str, port: int, timeout: float = 3.0) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(target, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, asyncio.TimeoutError):
        return False


async def _probe_redfish(target: str, username: str | None, password: str | None) -> tuple[bool, str]:
    try:
        await http_get_json(f"https://{target}/redfish/v1/", username=username, password=password)
        return True, "Redfish API reachable"
    except ConnectorError as exc:
        return False, str(exc)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


async def _probe_ssh_hostname(target: str, username: str, password: str) -> tuple[bool, str, str | None]:
    import paramiko

    def run() -> tuple[bool, str, str | None]:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(target, username=username, password=password, timeout=12)
        try:
            _, stdout, _ = client.exec_command("hostname -f 2>/dev/null || hostname")
            hostname = stdout.read().decode("utf-8", errors="replace").strip() or None
            return True, "SSH login succeeded", hostname
        finally:
            client.close()

    try:
        return await asyncio.to_thread(run)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), None


async def probe_target(
    target: str,
    *,
    username: str | None = None,
    password: str | None = None,
    device_type_hint: str | None = None,
) -> DiscoveryCandidate:
    settings = get_settings()
    if settings.mock_mode:
        suffix = target.split(".")[-1]
        return DiscoveryCandidate(
            target=target,
            reachable=True,
            detected_type=device_type_hint or "linux_ssh",
            suggested_name=f"discovered-{suffix}",
            suggested_hostname=f"discovered-{suffix}.local",
            credentials_ok=True if username and password else None,
            message="Mock discovery candidate",
        )

    reachable = await ping_host(target)
    if not reachable:
        return DiscoveryCandidate(
            target=target,
            reachable=False,
            message="Host unreachable (ping failed)",
        )

    detected: str | None = device_type_hint
    credentials_ok: bool | None = None
    message = "Host reachable"
    suggested_hostname: str | None = None

    redfish_open = await _port_open(target, 443)
    ssh_open = await _port_open(target, 22)

    if username and password:
        if device_type_hint == "hpe_ilorest" or (detected is None and redfish_open):
            ok, msg = await _probe_redfish(target, username, password)
            credentials_ok = ok
            message = msg
            if ok:
                detected = "hpe_ilorest"
        if device_type_hint == "linux_ssh" or (detected is None and ssh_open):
            ok, msg, hostname = await _probe_ssh_hostname(target, username, password)
            if credentials_ok is None or ok:
                credentials_ok = ok
                message = msg
            if ok:
                detected = detected or "linux_ssh"
                suggested_hostname = hostname
    else:
        if redfish_open:
            detected = detected or "hpe_ilorest"
            message = "Port 443 open — likely Redfish/iLO (credentials not tested)"
        elif ssh_open:
            detected = detected or "linux_ssh"
            message = "Port 22 open — likely SSH (credentials not tested)"

    name = suggested_hostname or f"host-{target.replace('.', '-')}"
    return DiscoveryCandidate(
        target=target,
        reachable=True,
        detected_type=detected,
        suggested_name=name.split(".")[0],
        suggested_hostname=suggested_hostname or name,
        credentials_ok=credentials_ok,
        message=message,
    )


async def scan_network(
    targets: list[str],
    *,
    username: str | None = None,
    password: str | None = None,
    device_type_hint: str | None = None,
) -> DiscoveryScanResult:
    if device_type_hint and device_type_hint not in DEVICE_TYPES:
        raise ValueError(f"Unsupported device_type_hint. Choose one of: {', '.join(DEVICE_TYPES)}")

    hosts = expand_targets(targets)
    results = await asyncio.gather(
        *(
            probe_target(
                host,
                username=username,
                password=password,
                device_type_hint=device_type_hint,
            )
            for host in hosts
        )
    )
    return DiscoveryScanResult(scanned=len(hosts), candidates=list(results))


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
            ok, msg, _ = await _probe_ssh_hostname(target, user, pwd)
            return CredentialTestResult(
                ok=ok,
                message=msg,
                device_type=device.device_type,
                overall="ok" if ok else "down",
            )
        if device.device_type == "linux_ssh":
            reachable = await ping_host(target)
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

        name = candidate.suggested_name or f"discovered-{candidate.target}"
        hostname = candidate.suggested_hostname or candidate.target
        payload = DeviceCreate(
            name=name,
            hostname=hostname,
            device_type=candidate.detected_type,
            management_ip=candidate.target,
            connector_enabled=enable_connectors,
            username=username if import_credentials else None,
            password=password if import_credentials else None,
        )
        device_service.create_device(db, payload)
        existing_hosts.add(candidate.target.lower())
        imported += 1

    return DiscoveryImportResult(imported=imported, skipped=skipped)