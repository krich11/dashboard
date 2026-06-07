"""Multi-method host fingerprinting for network discovery."""

from __future__ import annotations

import asyncio
import re

from app.collectors.helpers import ConnectorError, http_get_json, ping_host
from app.config import get_settings

FINGERPRINT_PORTS = (22, 443, 830, 161)
SSH_BANNER_RE = re.compile(r"SSH-[\d.]+-([^\r\n]+)")


async def port_open(target: str, port: int, timeout: float = 3.0) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(target, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, asyncio.TimeoutError):
        return False


async def probe_ports(target: str) -> dict[int, bool]:
    results = await asyncio.gather(*(port_open(target, port) for port in FINGERPRINT_PORTS))
    return dict(zip(FINGERPRINT_PORTS, results, strict=True))


async def grab_ssh_banner(target: str) -> tuple[bool, str | None]:
    def run() -> tuple[bool, str | None]:
        import socket

        try:
            with socket.create_connection((target, 22), timeout=5) as sock:
                banner = sock.recv(256).decode("utf-8", errors="replace").strip()
        except OSError:
            return False, None
        match = SSH_BANNER_RE.search(banner)
        return True, match.group(1) if match else banner[:80] or None

    return await asyncio.to_thread(run)


async def probe_redfish(
    target: str,
    username: str | None,
    password: str | None,
) -> tuple[bool, str, bool]:
    """Returns (reachable, message, authenticated)."""
    try:
        await http_get_json(f"https://{target}/redfish/v1/", username=username, password=password)
        if username and password:
            return True, "Redfish API authenticated", True
        return True, "Redfish API reachable", False
    except ConnectorError as exc:
        msg = str(exc)
        if "401" in msg or "403" in msg:
            return True, "Redfish endpoint present (auth required)", False
        return False, msg, False
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), False


async def probe_aruba_rest(
    target: str,
    username: str | None,
    password: str | None,
) -> tuple[bool, str, bool]:
    if not username or not password:
        return False, "Aruba REST requires credentials", False
    try:
        await http_get_json(
            f"https://{target}/rest/v1/system",
            username=username,
            password=password,
        )
        return True, "Aruba REST authenticated", True
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), False


async def probe_ssh_login(
    target: str,
    username: str,
    password: str,
) -> tuple[bool, str, str | None]:
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


async def probe_juniper_login(target: str, username: str, password: str) -> tuple[bool, str]:
    def run() -> tuple[bool, str]:
        try:
            from jnpr.junos import Device as JunosDevice
        except ImportError:
            return False, "junos-eznc not installed"

        try:
            with JunosDevice(host=target, user=username, passwd=password, timeout=15) as dev:
                dev.open()
                hostname = dev.facts.get("hostname", target)
                return True, f"Juniper NETCONF login succeeded ({hostname})"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    ok, msg = await asyncio.to_thread(run)
    if ok:
        return ok, msg
    ssh_ok, ssh_msg, _ = await probe_ssh_login(target, username, password)
    if ssh_ok:
        return True, f"Juniper SSH fallback: {ssh_msg}"
    return False, msg or ssh_msg


def _mock_fingerprint(target: str, device_type_hint: str | None) -> dict:
    suffix = target.replace(":", "-").replace(".", "-")
    detected = device_type_hint or "linux_ssh"
    return {
        "reachable": True,
        "detected_type": detected,
        "suggested_name": f"discovered-{suffix}",
        "suggested_hostname": f"discovered-{suffix}.local",
        "credentials_ok": True,
        "message": "Mock discovery candidate",
        "fingerprint_methods": ["mock"],
    }


async def fingerprint_target(
    target: str,
    *,
    username: str | None = None,
    password: str | None = None,
    device_type_hint: str | None = None,
) -> dict:
    settings = get_settings()
    if settings.mock_mode:
        return _mock_fingerprint(target, device_type_hint)

    methods: list[str] = []
    reachable = await ping_host(target)
    if reachable:
        methods.append("ping")

    ports = await probe_ports(target)
    for port, open_ in ports.items():
        if open_:
            methods.append(f"port_{port}")

    detected: str | None = device_type_hint
    credentials_ok: bool | None = None
    messages: list[str] = []
    suggested_hostname: str | None = None

    if ports.get(22):
        banner_ok, banner = await grab_ssh_banner(target)
        if banner_ok and banner:
            methods.append("ssh_banner")
            banner_lower = banner.lower()
            if "junos" in banner_lower or "juniper" in banner_lower:
                detected = detected or "juniper"
                messages.append(f"SSH banner suggests Juniper ({banner})")
            elif detected is None:
                detected = detected or "linux_ssh"
                messages.append(f"SSH banner: {banner}")

    if ports.get(830) and detected is None:
        detected = "juniper"
        messages.append("NETCONF port 830 open — likely Juniper")

    if ports.get(443):
        redfish_ok, redfish_msg, redfish_auth = await probe_redfish(target, username, password)
        if redfish_ok:
            methods.append("redfish")
            if redfish_auth:
                methods.append("redfish_auth")
                credentials_ok = True
                detected = detected or "hpe_ilorest"
            elif detected is None:
                detected = "hpe_ilorest"
            messages.append(redfish_msg)

    if username and password:
        if device_type_hint == "aruba" or (detected is None and ports.get(443)):
            aruba_ok, aruba_msg, aruba_auth = await probe_aruba_rest(target, username, password)
            if aruba_ok:
                methods.append("aruba_rest")
            if aruba_auth:
                methods.append("aruba_rest_auth")
                credentials_ok = True
                detected = detected or "aruba"
                messages.append(aruba_msg)

        if device_type_hint == "juniper" or (detected == "juniper" and ports.get(830)):
            jun_ok, jun_msg = await probe_juniper_login(target, username, password)
            methods.append("juniper_netconf" if jun_ok else "juniper_netconf_fail")
            if credentials_ok is None or jun_ok:
                credentials_ok = jun_ok
            if jun_ok:
                detected = "juniper"
            messages.append(jun_msg)

        if device_type_hint == "linux_ssh" or (detected is None and ports.get(22)):
            ssh_ok, ssh_msg, hostname = await probe_ssh_login(target, username, password)
            methods.append("ssh_login" if ssh_ok else "ssh_login_fail")
            if credentials_ok is None or ssh_ok:
                credentials_ok = ssh_ok
            if ssh_ok:
                detected = detected or "linux_ssh"
                suggested_hostname = hostname
            messages.append(ssh_msg)

        if device_type_hint == "hpe_ilorest" and credentials_ok is None:
            rf_ok, rf_msg, rf_auth = await probe_redfish(target, username, password)
            if rf_ok:
                methods.append("redfish_probe")
            credentials_ok = rf_auth
            if rf_auth:
                detected = "hpe_ilorest"
            messages.append(rf_msg)
    elif not messages:
        if ports.get(443):
            detected = detected or "hpe_ilorest"
            messages.append("Port 443 open — likely Redfish/iLO (credentials not tested)")
        elif ports.get(22):
            detected = detected or "linux_ssh"
            messages.append("Port 22 open — likely SSH (credentials not tested)")
        elif ports.get(830):
            detected = detected or "juniper"
            messages.append("Port 830 open — likely Juniper NETCONF (credentials not tested)")

    if not reachable and not methods:
        return {
            "reachable": False,
            "detected_type": None,
            "suggested_name": None,
            "suggested_hostname": None,
            "credentials_ok": None,
            "message": "Host unreachable (ping failed, no open fingerprint ports)",
            "fingerprint_methods": methods,
        }

    name = suggested_hostname or f"host-{target.replace('.', '-').replace(':', '-')}"
    message = "; ".join(messages) if messages else ("Host reachable" if reachable else "Fingerprint via open ports")
    return {
        "reachable": reachable or bool(methods),
        "detected_type": detected,
        "suggested_name": name.split(".")[0],
        "suggested_hostname": suggested_hostname or name,
        "credentials_ok": credentials_ok,
        "message": message,
        "fingerprint_methods": methods,
    }