from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.services import devices as device_service
from app.services.aggregation import compute_high_level_summary
from app.services.collector_service import collector_service

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def prometheus_metrics(db: Session = Depends(get_db)) -> Response:
    summary = compute_high_level_summary(db)
    status = collector_service.get_status(db)
    issues = device_service.list_issues(db, important_only=False)
    settings = get_settings()

    health_value = {"ok": 1, "degraded": 0.5, "down": 0, "unknown": -1}.get(
        summary.internet_health, -1
    )
    lines = [
        "# HELP dashboard_important_devices_total Total important devices tracked",
        "# TYPE dashboard_important_devices_total gauge",
        f"dashboard_important_devices_total {summary.important_total}",
        "# HELP dashboard_important_devices_up Important devices currently up",
        "# TYPE dashboard_important_devices_up gauge",
        f"dashboard_important_devices_up {summary.important_up}",
        "# HELP dashboard_important_devices_down Important devices currently down",
        "# TYPE dashboard_important_devices_down gauge",
        f"dashboard_important_devices_down {summary.important_down}",
        "# HELP dashboard_internet_health_score Internet health 1=ok 0.5=degraded 0=down",
        "# TYPE dashboard_internet_health_score gauge",
        f"dashboard_internet_health_score {health_value}",
        "# HELP dashboard_collector_running Collector scheduler running",
        "# TYPE dashboard_collector_running gauge",
        f"dashboard_collector_running {1 if status['running'] else 0}",
        "# HELP dashboard_mock_mode Mock mode enabled",
        "# TYPE dashboard_mock_mode gauge",
        f"dashboard_mock_mode {1 if settings.mock_mode else 0}",
        "# HELP dashboard_connector_enabled_devices Devices with connector polling enabled",
        "# TYPE dashboard_connector_enabled_devices gauge",
        f"dashboard_connector_enabled_devices {status['connector_enabled_devices']}",
        "# HELP dashboard_circuits_open Collector circuits currently open",
        "# TYPE dashboard_circuits_open gauge",
        f"dashboard_circuits_open {status['circuits_open']}",
        "# HELP dashboard_open_issues_total Devices with non-ok status",
        "# TYPE dashboard_open_issues_total gauge",
        f"dashboard_open_issues_total {len(issues)}",
    ]
    return Response(content="\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")