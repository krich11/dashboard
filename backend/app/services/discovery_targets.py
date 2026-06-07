"""Resolve default scan prefixes (RFC1918 + delegated IPv6) and expand to host lists."""

from __future__ import annotations

import ipaddress
import re
import subprocess

from app.config import get_settings

RFC1918_V4 = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)

IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def is_rfc1918_address(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.split("%")[0])
    except ValueError:
        return False
    if ip.version != 4:
        return False
    return any(ip in net for net in RFC1918_V4)


def is_rfc1918_network(net: ipaddress.IPv4Network) -> bool:
    return any(net.subnet_of(rfc) for rfc in RFC1918_V4)


def _mock_prefixes() -> list[str]:
    return ["10.0.0.0/24", "2001:db8:1000::/56"]


def _run_ip_route(family: int) -> str:
    flag = "-4" if family == 4 else "-6"
    try:
        result = subprocess.run(
            ["ip", flag, "route", "show"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return result.stdout or ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def parse_rfc1918_route_prefixes(route_output: str) -> list[str]:
    prefixes: list[str] = []
    for line in route_output.splitlines():
        token = line.split()[0] if line.split() else ""
        if "/" not in token:
            continue
        try:
            net = ipaddress.ip_network(token, strict=False)
        except ValueError:
            continue
        if not isinstance(net, ipaddress.IPv4Network) or not is_rfc1918_network(net):
            continue
        if net.prefixlen < 8 or net.prefixlen > 30:
            continue
        prefixes.append(str(net))
    return sorted(set(prefixes), key=lambda p: ipaddress.ip_network(p).prefixlen, reverse=True)


def parse_ipv6_delegated_prefixes(route_output: str) -> list[str]:
    prefixes: list[str] = []
    for line in route_output.splitlines():
        token = line.split()[0] if line.split() else ""
        if "/" not in token:
            continue
        try:
            net = ipaddress.ip_network(token, strict=False)
        except ValueError:
            continue
        if not isinstance(net, ipaddress.IPv6Network):
            continue
        if net.is_link_local or net.is_loopback or net.is_multicast:
            continue
        if net.subnet_of(ipaddress.ip_network("fc00::/7")):
            continue
        if net.prefixlen < 48 or net.prefixlen > 64:
            continue
        prefixes.append(str(net))
    return sorted(set(prefixes), key=lambda p: ipaddress.ip_network(p).prefixlen)


def get_default_scan_prefixes() -> list[str]:
    settings = get_settings()
    if settings.mock_mode or settings.testing:
        return _mock_prefixes()

    v4 = parse_rfc1918_route_prefixes(_run_ip_route(4))
    v6 = parse_ipv6_delegated_prefixes(_run_ip_route(6))
    if not v4 and not v6:
        v4 = ["192.168.0.0/24"]
    return v4 + v6


def _ipv6_scan_network(net: ipaddress.IPv6Network) -> ipaddress.IPv6Network:
    if net.prefixlen < 64:
        return ipaddress.ip_network(f"{net.network_address}/64", strict=False)
    return net


def sample_hosts_from_prefix(prefix: str, per_prefix_limit: int) -> list[str]:
    net = ipaddress.ip_network(prefix, strict=False)
    if net.version == 6:
        net = _ipv6_scan_network(net)
    hosts: list[str] = []
    for i, host in enumerate(net.hosts()):
        if i >= per_prefix_limit:
            break
        hosts.append(str(host))
    return hosts


def build_default_target_hosts(max_targets: int, per_prefix_limit: int = 64) -> tuple[list[str], list[str]]:
    prefixes = get_default_scan_prefixes()
    hosts: list[str] = []
    for prefix in prefixes:
        for host in sample_hosts_from_prefix(prefix, per_prefix_limit):
            hosts.append(host)
            if len(hosts) >= max_targets:
                return hosts, prefixes
    return hosts, prefixes


def expand_explicit_targets(
    targets: list[str],
    *,
    max_targets: int,
    rfc1918_only: bool = False,
) -> list[str]:
    expanded: list[str] = []
    for raw in targets:
        value = raw.strip()
        if not value:
            continue
        if "/" in value:
            try:
                net = ipaddress.ip_network(value, strict=False)
            except ValueError:
                continue
            if rfc1918_only and (
                isinstance(net, ipaddress.IPv4Network) and not is_rfc1918_network(net)
            ):
                continue
            for host in sample_hosts_from_prefix(value, max_targets):
                expanded.append(host)
                if len(expanded) >= max_targets:
                    return expanded
        else:
            if rfc1918_only and not is_rfc1918_address(value):
                try:
                    ip = ipaddress.ip_address(value.split("%")[0])
                    if ip.version == 4:
                        continue
                except ValueError:
                    continue
            expanded.append(value)
            if len(expanded) >= max_targets:
                return expanded
    return expanded