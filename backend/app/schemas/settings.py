from typing import Literal

from pydantic import BaseModel, Field, model_validator


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


class MockScenarioSettings(BaseModel):
    scenario: str
    available: list[str] = Field(default_factory=list)


class AlertSettings(BaseModel):
    enabled: bool = False
    webhook_url: str = ""
    min_interval_sec: int = Field(default=300, ge=60, le=3600)
    format: Literal["json", "slack", "pagerduty"] = "json"
    pagerduty_routing_key: str = ""


class AlertTestResult(BaseModel):
    ok: bool
    message: str


class CollectorRunResult(BaseModel):
    devices_polled: int
    reachability: bool


class CollectorStatus(BaseModel):
    running: bool
    mock_mode: bool
    total_devices: int
    connector_enabled_devices: int
    circuits_open: int
    devices_in_backoff: int


class HistorySettings(BaseModel):
    raw_days: int = Field(default=30, ge=1, le=365)
    hourly_days: int = Field(default=90, ge=2, le=3650)

    @model_validator(mode="after")
    def hourly_must_exceed_raw(self) -> "HistorySettings":
        if self.hourly_days <= self.raw_days:
            raise ValueError("hourly_days must be greater than raw_days")
        return self