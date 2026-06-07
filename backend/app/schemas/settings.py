from typing import Literal

from pydantic import BaseModel, Field


class ReachabilitySettings(BaseModel):
    ipv4_targets: list[str] = Field(default_factory=lambda: ["1.1.1.1", "8.8.8.8"])
    ipv6_targets: list[str] = Field(
        default_factory=lambda: ["2606:4700:4700::1111", "2001:4860:4860::8888"]
    )
    interval_sec: int = 60
    timeout_sec: int = 5
    method: Literal["ping", "http"] = "ping"
    require_both_families: bool = True
    http_url_v4: str = "https://1.1.1.1"
    http_url_v6: str = "https://[2606:4700:4700::1111]"


class CollectorSettings(BaseModel):
    interval_sec: int = Field(default=60, ge=10, le=3600)
    concurrency: int = Field(default=8, ge=1, le=64)
    default_backoff_sec: int = Field(default=30, ge=5, le=600)
    max_backoff_sec: int = Field(default=300, ge=30, le=3600)
    circuit_breaker_threshold: int = Field(default=5, ge=1, le=20)
    status_staleness_sec: int = Field(default=180, ge=30, le=3600)


class EncryptionStatus(BaseModel):
    configured: bool
    is_dev_default: bool
    key_source: str = "env"
    message: str


class EncryptionTestRequest(BaseModel):
    test_value: str = "dashboard-encryption-test"


class EncryptionTestResult(BaseModel):
    ok: bool
    message: str