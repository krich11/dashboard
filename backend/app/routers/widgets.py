from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/widgets", tags=["widgets"])

WIDGET_CATALOG = [
    {
        "type": "UpDownOverallStatus",
        "title": "Up/Down Overall Status",
        "description_for_llm": (
            "Large operational banner showing important device up/down counts and "
            "internet health summary. Config: title (string), showBreakdown (bool), "
            "refreshIntervalSec (number)."
        ),
        "priority": "P0",
        "data_source": "/api/v1/status/high-level",
    },
    {
        "type": "InternetReachability",
        "title": "Internet Reachability",
        "description_for_llm": (
            "Shows IPv4 and IPv6 reachability status with per-target results. "
            "Config: title, showTargets (bool), refreshIntervalSec (number)."
        ),
        "priority": "P0",
        "data_source": "/api/v1/reachability/latest",
    },
    {
        "type": "InternetHealthTrend",
        "title": "Internet Health Trend",
        "description_for_llm": (
            "Sparkline of internet reachability over time. "
            "Config: title, hours (number, default 24), refreshIntervalSec (number)."
        ),
        "priority": "P1",
        "data_source": "/api/v1/reachability/history",
    },
    {
        "type": "ImportantDevicesStatusGrid",
        "title": "Important Devices Grid",
        "description_for_llm": (
            "Compact grid of important devices with status. Config: title, maxItems (number)."
        ),
        "priority": "P1",
        "data_source": "/api/v1/devices?important=true",
    },
    {
        "type": "IssuesList",
        "title": "Issues List",
        "description_for_llm": (
            "List of current warnings and critical issues. Config: title, importantOnly (bool)."
        ),
        "priority": "P1",
        "data_source": "/api/v1/status/issues",
    },
    {
        "type": "InventoryTable",
        "title": "Inventory Table",
        "description_for_llm": (
            "Compact searchable inventory table widget. Config: title, maxRows (number)."
        ),
        "priority": "P1",
        "data_source": "/api/v1/devices/with-status",
    },
]


@router.get("/catalog")
def read_widget_catalog() -> list[dict]:
    return WIDGET_CATALOG