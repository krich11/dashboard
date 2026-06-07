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