import json
from datetime import datetime
from pathlib import Path

from app.config import ROOT_DIR
from app.schemas.device import DeviceRead, DeviceStatusRead
from app.schemas.reachability import ExternalReachabilityRead, ReachabilityTargetResult
from app.schemas.status import HighLevelSummary

MOCKS_DIR = ROOT_DIR / "mocks"


def _load_json(name: str) -> object:
    return json.loads((MOCKS_DIR / name).read_text())


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_scenario_payload(scenario: str | None = None) -> dict:
    scenarios = _load_json("scenarios.json")
    from app.config import get_settings

    key = scenario or get_settings().mock_scenario
    if key not in scenarios:
        key = "all_clear"
    return scenarios[key]


def get_high_level_summary(scenario: str | None = None) -> HighLevelSummary:
    payload = get_scenario_payload(scenario)
    data = payload["high_level"]
    data["timestamp"] = _parse_ts(data["timestamp"])
    return HighLevelSummary(**data)


def get_reachability_latest(scenario: str | None = None) -> ExternalReachabilityRead:
    payload = get_scenario_payload(scenario)
    data = payload["reachability"]
    data["timestamp"] = _parse_ts(data["timestamp"])
    data["ipv4_targets"] = [ReachabilityTargetResult(**t) for t in data["ipv4_targets"]]
    data["ipv6_targets"] = [ReachabilityTargetResult(**t) for t in data["ipv6_targets"]]
    return ExternalReachabilityRead(**data)


def get_devices() -> list[DeviceRead]:
    return [DeviceRead(**item) for item in _load_json("devices.json")]


def get_device_statuses(scenario: str | None = None) -> list[DeviceStatusRead]:
    if scenario:
        payload = get_scenario_payload(scenario)
        raw = payload["statuses"]
    else:
        raw = _load_json("statuses.json")
    results: list[DeviceStatusRead] = []
    for item in raw:
        item = dict(item)
        item["timestamp"] = _parse_ts(item["timestamp"])
        results.append(DeviceStatusRead(**item))
    return results