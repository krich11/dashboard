#!/usr/bin/env python3
"""Generate mock fixture files for Phase 0 (67 devices)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOCKS = ROOT / "mocks"

DEVICE_COUNTS = {
    "hpe_ilorest": 7,
    "juniper": 10,
    "aruba": 20,
    "linux_ssh": 30,
}

IMPORTANT_INDICES = {
    "hpe_ilorest": {0, 1, 2},
    "juniper": {0, 1},
    "aruba": {0, 1, 2, 3},
    "linux_ssh": {0, 1, 2, 3, 4, 5, 6, 7},
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def build_devices() -> list[dict]:
    devices: list[dict] = []
    for connector, count in DEVICE_COUNTS.items():
        prefix = connector.split("_")[0]
        for i in range(count):
            device_id = str(uuid.uuid4())
            devices.append(
                {
                    "id": device_id,
                    "name": f"{prefix}-{connector}-{i + 1:02d}",
                    "hostname": f"{prefix}{i + 1:02d}.dc.local",
                    "device_type": connector,
                    "tags": [prefix, connector],
                    "important_flag": i in IMPORTANT_INDICES.get(connector, set()),
                    "management_ip": f"10.0.{hash(connector) % 200}.{i + 10}",
                    "connector_enabled": False,
                }
            )
    return devices


def build_statuses(devices: list[dict], scenario: str = "all_clear") -> list[dict]:
    statuses: list[dict] = []
    down_ids: set[str] = set()
    if scenario == "devices_down":
        important = [d for d in devices if d["important_flag"]]
        down_ids = {d["id"] for d in important[:3]}
    elif scenario == "mixed":
        important = [d for d in devices if d["important_flag"]]
        down_ids = {d["id"] for d in important[:2]}

    for device in devices:
        overall = "ok"
        message = "Operational"
        if device["id"] in down_ids:
            overall = "down"
            message = "Unreachable"
        statuses.append(
            {
                "device_id": device["id"],
                "overall": overall,
                "message": message,
                "metrics": {
                    "cpu_pct": 35,
                    "mem_pct": 52,
                    "temp_c": 38,
                    "power_state": "on",
                },
                "details": {"connector": device["device_type"]},
                "timestamp": _now(),
            }
        )
    return statuses


def build_reachability(scenario: str = "all_clear") -> dict:
    ipv4_ok = True
    ipv6_ok = True
    overall = "ok"
    if scenario == "internet_degraded":
        ipv6_ok = False
        overall = "degraded"
    elif scenario == "mixed":
        ipv6_ok = False
        overall = "degraded"

    return {
        "ipv4_ok": ipv4_ok,
        "ipv6_ok": ipv6_ok,
        "ipv4_targets": [
            {"target": "1.1.1.1", "ok": ipv4_ok, "latency_ms": 12, "error": None},
            {"target": "8.8.8.8", "ok": ipv4_ok, "latency_ms": 14, "error": None},
        ],
        "ipv6_targets": [
            {
                "target": "2606:4700:4700::1111",
                "ok": ipv6_ok,
                "latency_ms": 18 if ipv6_ok else None,
                "error": None if ipv6_ok else "timeout",
            },
            {
                "target": "2001:4860:4860::8888",
                "ok": ipv6_ok,
                "latency_ms": 20 if ipv6_ok else None,
                "error": None if ipv6_ok else "timeout",
            },
        ],
        "overall": overall,
        "timestamp": _now(),
    }


def build_high_level(devices: list[dict], reachability: dict, scenario: str) -> dict:
    important = [d for d in devices if d["important_flag"]]
    statuses = build_statuses(devices, scenario)
    status_by_id = {s["device_id"]: s for s in statuses}
    important_down = sum(
        1
        for d in important
        if status_by_id[d["id"]]["overall"] in {"down", "critical", "unknown"}
    )
    important_up = len(important) - important_down
    internet_health = reachability["overall"]
    if reachability["overall"] == "ok":
        internet_health = "ok"
    elif reachability["overall"] == "degraded":
        internet_health = "degraded"
    else:
        internet_health = "down"

    if important_down > 0 and internet_health != "ok":
        banner = "mixed"
        banner_text = f"{important_down} Important Devices Down; Internet Degraded"
        worst = "critical"
    elif important_down > 0:
        banner = "devices_down"
        banner_text = f"{important_down} Important Devices Down"
        worst = "critical"
    elif internet_health != "ok":
        banner = "internet_degraded"
        banner_text = "Internet Degraded"
        worst = "warning"
    else:
        banner = "all_clear"
        banner_text = "All Systems Operational"
        worst = "ok"

    ipv4 = "OK" if reachability["ipv4_ok"] else "Down"
    ipv6 = "OK" if reachability["ipv6_ok"] else "Degraded"
    return {
        "banner": banner,
        "banner_text": banner_text,
        "important_total": len(important),
        "important_up": important_up,
        "important_down": important_down,
        "internet_health": internet_health,
        "internet_summary": f"IPv4 {ipv4}, IPv6 {ipv6}",
        "worst_overall": worst,
        "timestamp": _now(),
    }


def main() -> None:
    MOCKS.mkdir(parents=True, exist_ok=True)
    devices = build_devices()
    assert len(devices) == 67, f"expected 67 devices, got {len(devices)}"

    scenarios = {
        "all_clear": ("all_clear", "all_clear"),
        "devices_down": ("devices_down", "all_clear"),
        "internet_degraded": ("all_clear", "internet_degraded"),
        "mixed": ("mixed", "internet_degraded"),
    }

    (MOCKS / "devices.json").write_text(json.dumps(devices, indent=2))
    (MOCKS / "statuses.json").write_text(
        json.dumps(build_statuses(devices, "all_clear"), indent=2)
    )
    (MOCKS / "reachability.json").write_text(
        json.dumps(build_reachability("all_clear"), indent=2)
    )

    scenario_payloads = {}
    for name, (device_scenario, reach_scenario) in scenarios.items():
        reach = build_reachability(reach_scenario)
        scenario_payloads[name] = {
            "high_level": build_high_level(devices, reach, device_scenario),
            "reachability": reach,
            "statuses": build_statuses(devices, device_scenario),
        }
    (MOCKS / "scenarios.json").write_text(json.dumps(scenario_payloads, indent=2))
    print(f"Wrote {len(devices)} devices to {MOCKS}")


if __name__ == "__main__":
    main()