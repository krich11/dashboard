"""Multi-method host fingerprinting for network discovery."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from app.collectors.helpers import ConnectorError, http_get_json, ping_host
from app.config import get_settings

if TYPE_CHECKING:
    from app.services.credential_profiles_service import ResolvedCredential

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
    username: str,
    password: str,
) -> tuple[bool, str, bool]:
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


def _mock_fingerprint(
    target: str,
    device_type_hint: str | None,
    credential_attempts: list[ResolvedCredential] | None,
) -> dict:
    suffix = target.replace(":", "-").replace(".", "-")
    detected = device_type_hint or "linux_ssh"
    matched = credential_attempts[0] if credential_attempts else None
    return {
        "reachable": True,
        "detected_type": detected,
        "suggested_name": f"discovered-{suffix}",
        "suggested_hostname": f"discovered-{suffix}.local",
        "credentials_ok": bool(credential_attempts),
        "message": "Mock discovery candidate",
        "fingerprint_methods": ["mock"],
        "matched_credential_profile_id": matched.profile_id if matched else None,
        "matched_credential_profile_name": (matched.profile_name or matched.username) if matched else None,
    }


async def _try_credential_set(
    target: str,
    *,
    username: str,
    password: str,
    profile_label: str | None,
    detected: str | None,
    device_type_hint: str | None,
    ports: dict[int, bool],
    methods: list[str],
) -> dict | None:
    messages: list[str] = []
    credentials_ok = False
    suggested_hostname: str | None = None
    local_detected = detected

    if device_type_hint == "aruba" or local_detected == "aruba" or ports.get(443):
        aruba_ok, aruba_msg, aruba_auth = await probe_aruba_rest(target, username, password)
        if aruba_ok:
            methods.append("aruba_rest")
        if aruba_auth:
            methods.append("aruba_rest_auth")
            credentials_ok = True
            local_detected = local_detected or "aruba"
            prefix = f"[{profile_label}] " if profile_label else ""
            return {
                "credentials_ok": True,
                "detected_type": local_detected,
                "suggested_hostname": suggested_hostname,
                "message": f"{prefix}{aruba_msg}",
                "matched_credential_profile_id": None,
                "matched_credential_profile_name": profile_label,
            }
        messages.append(aruba_msg)

    if device_type_hint == "juniper" or local_detected == "juniper" or ports.get(830):
        jun_ok, jun_msg = await probe_juniper_login(target, username, password)
        methods.append("juniper_netconf" if jun_ok else "juniper_netconf_fail")
        if jun_ok:
            credentials_ok = True
            local_detected = "juniper"
            prefix = f"[{profile_label}] " if profile_label else ""
            return {
                "credentials_ok": True,
                "detected_type": local_detected,
                "suggested_hostname": suggested_hostname,
                "message": f"{prefix}{jun_msg}",
                "matched_credential_profile_id": None,
                "matched_credential_profile_name": profile_label,
            }
        messages.append(jun_msg)

    if device_type_hint == "linux_ssh" or local_detected == "linux_ssh" or ports.get(22):
        ssh_ok, ssh_msg, hostname = await probe_ssh_login(target, username, password)
        methods.append("ssh_login" if ssh_ok else "ssh_login_fail")
        if ssh_ok:
            credentials_ok = True
            local_detected = local_detected or "linux_ssh"
            suggested_hostname = hostname
            prefix = f"[{profile_label}] " if profile_label else ""
            return {
                "credentials_ok": True,
                "detected_type": local_detected,
                "suggested_hostname": suggested_hostname,
                "message": f"{prefix}{ssh_msg}",
                "matched_credential_profile_id": None,
                "matched_credential_profile_name": profile_label,
            }
        messages.append(ssh_msg)

    if device_type_hint == "hpe_ilorest" or local_detected == "hpe_ilorest" or ports.get(443):
        rf_ok, rf_msg, rf_auth = await probe_redfish(target, username, password)
        if rf_ok:
            methods.append("redfish_probe")
        if rf_auth:
            credentials_ok = True
            local_detected = local_detected or "hpe_ilorest"
            prefix = f"[{profile_label}] " if profile_label else ""
            return {
                "credentials_ok": True,
                "detected_type": local_detected,
                "suggested_hostname": suggested_hostname,
                "message": f"{prefix}{rf_msg}",
                "matched_credential_profile_id": None,
                "matched_credential_profile_name": profile_label,
            }
        messages.append(rf_msg)

    if credentials_ok:
        prefix = f"[{profile_label}] " if profile_label else ""
        return {
            "credentials_ok": True,
            "detected_type": local_detected,
            "suggested_hostname": suggested_hostname,
            "message": prefix + "; ".join(messages),
            "matched_credential_profile_id": None,
            "matched_credential_profile_name": profile_label,
        }
    return None


async def fingerprint_target(
    target: str,
    *,
    username: str | None = None,
    password: str | None = None,
    device_type_hint: str | None = None,
    credential_attempts: list[ResolvedCredential] | None = None,
) -> dict:
    settings = get_settings()
    attempts = list(credential_attempts or [])
    if username and password and not any(
        a.username == username and a.password == password for a in attempts
    ):
        from app.services.credential_profiles_service import ResolvedCredential

        attempts.insert(
            0,
            ResolvedCredential(
                profile_id=None,
                profile_name="manual",
                username=username,
                password=password,
                device_types=(),
            ),
        )

    if settings.mock_mode:
        return _mock_fingerprint(target, device_type_hint, attempts)

    methods: list[str] = []
    reachable, _latency = await ping_host(target)
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
    matched_profile_id: str | None = None
    matched_profile_name: str | None = None

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
        redfish_ok, redfish_msg, _ = await probe_redfish(target, None, None)
        if redfish_ok:
            methods.append("redfish")
            if detected is None:
                detected = "hpe_ilorest"
            messages.append(redfish_msg)

    for attempt in attempts:
        label = attempt.profile_name or attempt.username
        result = await _try_credential_set(
            target,
            username=attempt.username,
            password=attempt.password,
            profile_label=label,
            detected=detected,
            device_type_hint=device_type_hint,
            ports=ports,
            methods=methods,
        )
        if result and result.get("credentials_ok"):
            credentials_ok = True
            detected = result.get("detected_type") or detected
            suggested_hostname = result.get("suggested_hostname") or suggested_hostname
            matched_profile_id = attempt.profile_id
            matched_profile_name = attempt.profile_name or label
            messages.append(result["message"])
            break

    if credentials_ok is None and not messages:
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
            "matched_credential_profile_id": None,
            "matched_credential_profile_name": None,
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
        "matched_credential_profile_id": matched_profile_id,
        "matched_credential_profile_name": matched_profile_name,
    }