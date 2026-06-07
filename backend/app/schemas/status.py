from datetime import datetime
from typing import Literal

from pydantic import BaseModel

BannerType = Literal["all_clear", "devices_down", "internet_degraded", "mixed"]
HealthType = Literal["ok", "degraded", "down", "warning", "critical", "unknown"]


class HighLevelSummary(BaseModel):
    banner: BannerType
    banner_text: str
    important_total: int
    important_up: int
    important_down: int
    internet_health: HealthType
    internet_summary: str
    worst_overall: HealthType
    timestamp: datetime