from datetime import UTC, datetime

DOWN_STATUSES = {"down", "critical", "unknown"}
WARNING_STATUSES = {"warning"}


def normalize_overall(raw: str) -> str:
    value = (raw or "unknown").lower()
    if value in {"ok", "up", "healthy", "online"}:
        return "ok"
    if value in {"warn", "warning", "degraded"}:
        return "warning"
    if value in {"crit", "critical", "error", "failed"}:
        return "critical"
    if value in {"down", "offline", "unreachable"}:
        return "down"
    return "unknown"


def is_device_up(overall: str, polled_at: datetime, staleness_sec: int) -> bool:
    if normalize_overall(overall) in DOWN_STATUSES:
        return False
    now = datetime.now(UTC)
    polled_utc = polled_at.replace(tzinfo=UTC) if polled_at.tzinfo is None else polled_at.astimezone(UTC)
    age = (now - polled_utc).total_seconds()
    return age <= staleness_sec


def build_status_message(overall: str, detail: str | None = None) -> str:
    normalized = normalize_overall(overall)
    defaults = {
        "ok": "Operational",
        "warning": "Warning",
        "critical": "Critical",
        "down": "Unreachable",
        "unknown": "Unknown",
    }
    base = defaults.get(normalized, "Unknown")
    return f"{base}: {detail}" if detail else base