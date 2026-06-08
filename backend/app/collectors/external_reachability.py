from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.reachability import ExternalReachabilityResult
from app.models.settings import AppSettings
from app.schemas.reachability import ExternalReachabilityRead, ReachabilityTargetResult
from app.schemas.settings import ReachabilitySettings

CheckFn = Callable[[str, str, int], Awaitable[tuple[bool, int | None, str | None]]]


async def _ping_target(target: str, family: str, timeout_sec: int) -> tuple[bool, int | None, str | None]:
    from app.collectors.helpers import ping_host

    try:
        ok = await ping_host(target, timeout_sec=timeout_sec, family=family)
        return ok, None, None if ok else "ping failed"
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)


async def _http_target(url: str, _family: str, timeout_sec: int) -> tuple[bool, int | None, str | None]:
    try:
        async with httpx.AsyncClient(timeout=timeout_sec, verify=False) as client:
            start = datetime.now(UTC)
            response = await client.get(url)
            latency = int((datetime.now(UTC) - start).total_seconds() * 1000)
            ok = response.status_code < 500
            return ok, latency, None if ok else f"HTTP {response.status_code}"
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)


def _resolve_mock_scenario(db: Session | None) -> str:
    if db is not None:
        from app.services.mock_scenario import get_active_mock_scenario

        return get_active_mock_scenario(db)
    return get_settings().mock_scenario


async def _mock_target(
    _target: str, family: str, _timeout_sec: int, scenario: str
) -> tuple[bool, int | None, str | None]:
    if scenario == "internet_degraded":
        return family == "ipv4", 10, None if family == "ipv4" else "mock degraded"
    if scenario == "mixed":
        return family == "ipv4", 12, None if family == "ipv4" else "mock degraded"
    if scenario == "devices_down":
        return True, 10, None
    return True, 10, None


class ExternalReachabilityMonitor:
    def __init__(self, db: Session, check_fn: CheckFn | None = None) -> None:
        self.db = db
        self._check_fn = check_fn

    def load_settings(self) -> ReachabilitySettings:
        row = self.db.get(AppSettings, "reachability")
        if row and row.value:
            return ReachabilitySettings(**row.value)
        settings = get_settings()
        return ReachabilitySettings(
            ipv4_targets=settings.reachability_ipv4_targets,
            ipv6_targets=settings.reachability_ipv6_targets,
            interval_sec=settings.reachability_interval_sec,
            timeout_sec=settings.reachability_timeout_sec,
            method=settings.reachability_method,  # type: ignore[arg-type]
            require_both_families=settings.reachability_require_both_families,
        )

    def _resolve_check_fn(self, settings: ReachabilitySettings) -> CheckFn:
        if self._check_fn:
            return self._check_fn
        if get_settings().mock_mode:
            scenario = _resolve_mock_scenario(self.db)

            async def mock_check(
                target: str, family: str, timeout_sec: int
            ) -> tuple[bool, int | None, str | None]:
                return await _mock_target(target, family, timeout_sec, scenario)

            return mock_check
        if settings.method == "http":
            return _http_target
        return _ping_target

    async def _check_targets(
        self,
        targets: list[str],
        family: str,
        settings: ReachabilitySettings,
        check_fn: CheckFn,
    ) -> list[ReachabilityTargetResult]:
        results: list[ReachabilityTargetResult] = []
        for target in targets:
            if settings.method == "http":
                url = settings.http_url_v6 if family == "ipv6" else settings.http_url_v4
                ok, latency, error = await check_fn(url, family, settings.timeout_sec)
                results.append(
                    ReachabilityTargetResult(target=target, ok=ok, latency_ms=latency, error=error)
                )
            else:
                ok, latency, error = await check_fn(target, family, settings.timeout_sec)
                results.append(
                    ReachabilityTargetResult(target=target, ok=ok, latency_ms=latency, error=error)
                )
        return results

    async def run_once(self) -> ExternalReachabilityRead:
        settings = self.load_settings()
        check_fn = self._resolve_check_fn(settings)
        ipv4_targets = await self._check_targets(settings.ipv4_targets, "ipv4", settings, check_fn)
        ipv6_targets = await self._check_targets(settings.ipv6_targets, "ipv6", settings, check_fn)
        ipv4_ok = all(t.ok for t in ipv4_targets) if ipv4_targets else False
        ipv6_ok = all(t.ok for t in ipv6_targets) if ipv6_targets else False

        if settings.require_both_families:
            if ipv4_ok and ipv6_ok:
                overall = "ok"
            elif ipv4_ok or ipv6_ok:
                overall = "degraded"
            else:
                overall = "down"
        else:
            overall = "ok" if (ipv4_ok or ipv6_ok) else "down"

        timestamp = datetime.now(UTC)
        row = ExternalReachabilityResult(
            ipv4_ok=ipv4_ok,
            ipv6_ok=ipv6_ok,
            ipv4_targets=[t.model_dump() for t in ipv4_targets],
            ipv6_targets=[t.model_dump() for t in ipv6_targets],
            overall=overall,
            timestamp=timestamp.replace(tzinfo=None),
        )
        self.db.add(row)
        self.db.commit()

        return ExternalReachabilityRead(
            ipv4_ok=ipv4_ok,
            ipv6_ok=ipv6_ok,
            ipv4_targets=ipv4_targets,
            ipv6_targets=ipv6_targets,
            overall=overall,
            timestamp=timestamp,
        )