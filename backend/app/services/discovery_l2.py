"""Layer-2 neighbor discovery via infrastructure device ARP/MAC tables."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.collectors.helpers import ConnectorError, device_credentials, device_target, http_get_json
from app.config import get_settings
from app.models.device import Device
from app.services import devices as device_service
from app.services.credential_profiles_service import ResolvedCredential
from app.services.discovery_targets import IPV4_RE

MAC_RE = re.compile(r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}")
INFRA_TYPES = frozenset({"juniper", "aruba", "linux_ssh"})


@dataclass
class L2Neighbor:
    address: str
    mac: str | None = None
    vlan: str | None = None
    source_device_id: str = ""
    source_device_name: str = ""
    source_method: str = ""


def _parse_ipv4_from_text(text: str) -> set[str]:
    found: set[str] = set()
    for match in IPV4_RE.findall(text):
        parts = match.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            found.add(match)
    return found


def _parse_mac_from_line(line: str) -> str | None:
    match = MAC_RE.search(line)
    if not match:
        return None
    return match.group(0).lower().replace("-", ":")


def _parse_juniper_arp(output: str, source: L2Neighbor) -> list[L2Neighbor]:
    neighbors: list[L2Neighbor] = []
    for line in output.splitlines():
        ip_match = IPV4_RE.search(line)
        if not ip_match:
            continue
        mac = _parse_mac_from_line(line)
        neighbors.append(
            L2Neighbor(
                address=ip_match.group(0),
                mac=mac,
                source_device_id=source.source_device_id,
                source_device_name=source.source_device_name,
                source_method="juniper_arp",
            )
        )
    return neighbors


def _parse_juniper_mac_table(output: str, source: L2Neighbor, method: str) -> list[L2Neighbor]:
    neighbors: list[L2Neighbor] = []
    for line in output.splitlines():
        mac = _parse_mac_from_line(line)
        if not mac:
            continue
        ip_match = IPV4_RE.search(line)
        neighbors.append(
            L2Neighbor(
                address=ip_match.group(0) if ip_match else mac,
                mac=mac,
                source_device_id=source.source_device_id,
                source_device_name=source.source_device_name,
                source_method=method,
            )
        )
    return neighbors


def _parse_linux_neigh(output: str, source: L2Neighbor) -> list[L2Neighbor]:
    neighbors: list[L2Neighbor] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 1:
            continue
        addr = parts[0]
        if addr.endswith(":") and "%" not in addr:
            continue
        mac = _parse_mac_from_line(line)
        if "REACHABLE" in line or "STALE" in line or "DELAY" in line or mac:
            neighbors.append(
                L2Neighbor(
                    address=addr.split("%")[0],
                    mac=mac,
                    source_device_id=source.source_device_id,
                    source_device_name=source.source_device_name,
                    source_method="linux_neigh",
                )
            )
    return neighbors


def _juniper_cli_neighbors(host: str, username: str, password: str, source: L2Neighbor) -> list[L2Neighbor]:
    commands = (
        "show arp no-resolve",
        "show ethernet-switching table",
        "show bridge mac-table",
    )
    neighbors: list[L2Neighbor] = []

    try:
        from jnpr.junos import Device as JunosDevice
    except ImportError:
        return _ssh_cli_neighbors(host, username, password, source, commands)

    try:
        with JunosDevice(host=host, user=username, passwd=password, timeout=20) as dev:
            dev.open()
            for cmd in commands:
                output = dev.cli(cmd, warning=False)
                if "arp" in cmd:
                    neighbors.extend(_parse_juniper_arp(output, source))
                else:
                    method = "juniper_mac_table" if "ethernet" in cmd else "juniper_bridge_mac"
                    neighbors.extend(_parse_juniper_mac_table(output, source, method))
    except Exception:
        return _ssh_cli_neighbors(host, username, password, source, commands)
    return neighbors


def _ssh_cli_neighbors(
    host: str,
    username: str,
    password: str,
    source: L2Neighbor,
    commands: tuple[str, ...],
) -> list[L2Neighbor]:
    import paramiko

    neighbors: list[L2Neighbor] = []
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, timeout=15)
    try:
        for cmd in commands:
            _, stdout, _ = client.exec_command(cmd, timeout=30)
            output = stdout.read().decode("utf-8", errors="replace")
            if "arp" in cmd or "neigh" in cmd:
                if "junos" in cmd or "arp no-resolve" in cmd:
                    neighbors.extend(_parse_juniper_arp(output, source))
                else:
                    neighbors.extend(_parse_linux_neigh(output, source))
            else:
                method = "ssh_mac_table"
                neighbors.extend(_parse_juniper_mac_table(output, source, method))
    finally:
        client.close()
    return neighbors


def _linux_ssh_neighbors(host: str, username: str, password: str, source: L2Neighbor) -> list[L2Neighbor]:
    commands = ("ip -4 neigh show", "ip -6 neigh show", "arp -an 2>/dev/null || cat /proc/net/arp")
    return _ssh_cli_neighbors(host, username, password, source, commands)


async def _aruba_rest_neighbors(host: str, username: str, password: str, source: L2Neighbor) -> list[L2Neighbor]:
    neighbors: list[L2Neighbor] = []
    paths = (
        f"https://{host}/rest/v1/system/arp",
        f"https://{host}/rest/v1/system/mac-table",
    )
    for url in paths:
        try:
            data = await http_get_json(url, username=username, password=password)
        except ConnectorError:
            continue
        items = data if isinstance(data, list) else data.get("data", data.get("entries", []))
        if not isinstance(items, list):
            continue
        method = "aruba_arp" if "arp" in url else "aruba_mac_table"
        for item in items:
            if not isinstance(item, dict):
                continue
            addr = (
                item.get("ip")
                or item.get("ip_address")
                or item.get("ipv4")
                or item.get("mac")
                or item.get("mac_address")
            )
            if not addr:
                continue
            mac = item.get("mac") or item.get("mac_address")
            neighbors.append(
                L2Neighbor(
                    address=str(addr),
                    mac=str(mac).lower() if mac else None,
                    vlan=str(item.get("vlan")) if item.get("vlan") else None,
                    source_device_id=source.source_device_id,
                    source_device_name=source.source_device_name,
                    source_method=method,
                )
            )
    return neighbors


def _mock_l2_neighbors(device: Device) -> list[L2Neighbor]:
    base = device.management_ip or device.hostname or "10.0.0.1"
    octets = base.split(".")
    if len(octets) == 4:
        prefix = ".".join(octets[:3])
        addresses = [f"{prefix}.{n}" for n in (20, 21, 22, 50)]
    else:
        addresses = ["10.0.0.20", "10.0.0.21", "10.0.0.22"]
    return [
        L2Neighbor(
            address=addr,
            mac=f"00:11:22:33:44:{i:02x}",
            source_device_id=device.id,
            source_device_name=device.name,
            source_method="mock_arp",
        )
        for i, addr in enumerate(addresses, start=1)
    ]


async def _collect_with_login(
    device: Device,
    target: str,
    source: L2Neighbor,
    username: str,
    password: str,
) -> list[L2Neighbor]:
    if device.device_type == "juniper":
        return await asyncio.to_thread(_juniper_cli_neighbors, target, username, password, source)
    if device.device_type == "linux_ssh":
        return await asyncio.to_thread(_linux_ssh_neighbors, target, username, password, source)
    if device.device_type == "aruba":
        rest = await _aruba_rest_neighbors(target, username, password, source)
        if rest:
            return rest
        commands = ("show arp", "show mac-address-table")
        return await asyncio.to_thread(_ssh_cli_neighbors, target, username, password, source, commands)
    return []


async def collect_from_device(
    device: Device,
    *,
    username: str | None = None,
    password: str | None = None,
    credential_attempts: list[ResolvedCredential] | None = None,
) -> list[L2Neighbor]:
    settings = get_settings()
    if settings.mock_mode:
        return _mock_l2_neighbors(device)

    if device.device_type not in INFRA_TYPES:
        return []

    target = device_target(device)
    source = L2Neighbor(
        address=target,
        source_device_id=device.id,
        source_device_name=device.name,
    )

    attempts: list[tuple[str, str]] = []
    stored_user, stored_pass = device_credentials(device)
    if stored_user and stored_pass:
        attempts.append((stored_user, stored_pass))
    if username and password:
        attempts.append((username, password))
    for attempt in credential_attempts or []:
        if not attempt.device_types or device.device_type in attempt.device_types:
            attempts.append((attempt.username, attempt.password))

    seen: set[tuple[str, str]] = set()
    for user, pwd in attempts:
        key = (user, pwd)
        if key in seen:
            continue
        seen.add(key)
        found = await _collect_with_login(device, target, source, user, pwd)
        if found:
            return found
    return []


async def collect_l2_neighbors(
    db: Session,
    device_ids: list[str],
    *,
    username: str | None = None,
    password: str | None = None,
    credential_attempts: list[ResolvedCredential] | None = None,
) -> tuple[list[L2Neighbor], list[str]]:
    neighbors: list[L2Neighbor] = []
    sources: list[str] = []
    for device_id in device_ids:
        device = device_service.get_device(db, device_id)
        if device is None:
            continue
        if device.device_type not in INFRA_TYPES:
            continue
        found = await collect_from_device(
            device,
            username=username,
            password=password,
            credential_attempts=credential_attempts,
        )
        if found:
            neighbors.extend(found)
            sources.append(f"{device.name} ({device.device_type})")
    return neighbors, sources


def neighbor_addresses(neighbors: list[L2Neighbor]) -> list[str]:
    seen: set[str] = set()
    addresses: list[str] = []
    for neighbor in neighbors:
        addr = neighbor.address.split("%")[0]
        if addr in seen:
            continue
        seen.add(addr)
        addresses.append(addr)
    return addresses