from datetime import datetime

from pydantic import BaseModel


class ReachabilityTargetResult(BaseModel):
    target: str
    ok: bool
    latency_ms: int | None = None
    error: str | None = None


class ExternalReachabilityRead(BaseModel):
    ipv4_ok: bool
    ipv6_ok: bool
    ipv4_targets: list[ReachabilityTargetResult]
    ipv6_targets: list[ReachabilityTargetResult]
    overall: str
    timestamp: datetime