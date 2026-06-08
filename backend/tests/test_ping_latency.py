import pytest

from app.collectors.external_reachability import _ping_target


@pytest.mark.asyncio
async def test_ping_target_returns_latency(monkeypatch):
    async def fake_ping(_target: str, timeout_sec: int = 5, *, family: str | None = None):
        return True, 24

    monkeypatch.setattr("app.collectors.helpers.ping_host", fake_ping)

    ok, latency, error = await _ping_target("1.1.1.1", "ipv4", 2)
    assert ok is True
    assert latency == 24
    assert error is None