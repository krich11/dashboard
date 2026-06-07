import pytest

from app.collectors.external_reachability import ExternalReachabilityMonitor
from app.db.session import SessionLocal


async def _fake_check(target: str, family: str, timeout_sec: int):
    if family == "ipv6":
        return False, None, "timeout"
    return True, 5, None


@pytest.mark.asyncio
async def test_erm_persists_degraded_result():
    db = SessionLocal()
    try:
        monitor = ExternalReachabilityMonitor(db, check_fn=_fake_check)
        result = await monitor.run_once()
        assert result.ipv4_ok is True
        assert result.ipv6_ok is False
        assert result.overall == "degraded"
        latest = monitor.load_settings()
        assert latest.require_both_families is True
    finally:
        db.close()