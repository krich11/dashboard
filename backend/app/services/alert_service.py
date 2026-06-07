import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.alert_event import AlertEvent
from app.models.settings import AppSettings
from app.schemas.alerts import AlertEventRead
from app.schemas.settings import AlertSettings, AlertTestResult
from app.schemas.status import HighLevelSummary

logger = logging.getLogger(__name__)

BANNER_EMOJI = {
    "all_clear": ":white_check_mark:",
    "devices_down": ":rotating_light:",
    "internet_degraded": ":warning:",
    "mixed": ":fire:",
}


def get_alert_settings(db: Session) -> AlertSettings:
    row = db.get(AppSettings, "alerts")
    if row and row.value:
        return AlertSettings(**row.value)
    return AlertSettings()


def update_alert_settings(db: Session, payload: AlertSettings) -> AlertSettings:
    row = db.get(AppSettings, "alerts")
    if row is None:
        row = AppSettings(key="alerts", value=payload.model_dump())
        db.add(row)
    else:
        row.value = payload.model_dump()
    db.commit()
    return payload


def _get_alert_state(db: Session) -> dict:
    row = db.get(AppSettings, "alert_state")
    return row.value if row and row.value else {}


def _set_alert_state(db: Session, state: dict) -> None:
    row = db.get(AppSettings, "alert_state")
    if row is None:
        row = AppSettings(key="alert_state", value=state)
        db.add(row)
    else:
        row.value = state
    db.commit()


def build_json_payload(summary: HighLevelSummary, *, test: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": "banner_test" if test else "banner_change",
        "banner": summary.banner,
        "banner_text": summary.banner_text,
        "important_down": summary.important_down,
        "important_total": summary.important_total,
        "important_up": summary.important_up,
        "internet_health": summary.internet_health,
        "internet_summary": summary.internet_summary,
        "timestamp": summary.timestamp.isoformat(),
    }
    if test:
        payload["test"] = True
    return payload


def build_slack_payload(summary: HighLevelSummary, *, test: bool = False) -> dict[str, Any]:
    emoji = BANNER_EMOJI.get(summary.banner, ":grey_question:")
    prefix = "[TEST] " if test else ""
    text = (
        f"{prefix}{emoji} *{summary.banner_text}*\n"
        f"Important: {summary.important_up}/{summary.important_total} up"
        f" ({summary.important_down} down)\n"
        f"Internet: {summary.internet_health} — {summary.internet_summary}"
    )
    return {
        "text": f"{prefix}Datacenter Dashboard: {summary.banner_text}",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
        ],
    }


def build_pagerduty_payload(
    settings: AlertSettings, summary: HighLevelSummary, *, test: bool = False
) -> dict[str, Any]:
    severity = "info"
    if summary.banner in {"devices_down", "mixed"}:
        severity = "critical"
    elif summary.banner == "internet_degraded":
        severity = "warning"
    elif summary.banner == "all_clear":
        severity = "info"

    payload: dict[str, Any] = {
        "event_action": "trigger",
        "payload": {
            "summary": ("[TEST] " if test else "") + summary.banner_text,
            "severity": severity,
            "source": "datacenter-dashboard",
            "component": "operations-banner",
            "group": "datacenter",
            "class": summary.banner,
            "custom_details": {
                "important_down": summary.important_down,
                "important_total": summary.important_total,
                "internet_health": summary.internet_health,
                "internet_summary": summary.internet_summary,
            },
        },
    }
    if settings.pagerduty_routing_key:
        payload["routing_key"] = settings.pagerduty_routing_key
    return payload


def build_webhook_payload(
    settings: AlertSettings, summary: HighLevelSummary, *, test: bool = False
) -> dict[str, Any]:
    if settings.format == "slack":
        return build_slack_payload(summary, test=test)
    if settings.format == "pagerduty":
        return build_pagerduty_payload(settings, summary, test=test)
    return build_json_payload(summary, test=test)


async def send_webhook(
    settings: AlertSettings, summary: HighLevelSummary, *, test: bool = False
) -> None:
    payload = build_webhook_payload(settings, summary, test=test)
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(settings.webhook_url, json=payload)
        response.raise_for_status()


def record_alert_event(
    db: Session,
    *,
    event_type: str,
    severity: str,
    message: str,
    payload: dict[str, Any],
) -> AlertEvent:
    row = AlertEvent(
        event_type=event_type,
        severity=severity,
        message=message,
        payload=payload,
        acknowledged=False,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_alert_events(
    db: Session, *, limit: int = 50, acknowledged: bool | None = None
) -> list[AlertEventRead]:
    query = db.query(AlertEvent).order_by(AlertEvent.created_at.desc())
    if acknowledged is not None:
        query = query.filter(AlertEvent.acknowledged.is_(acknowledged))
    return [AlertEventRead.model_validate(row) for row in query.limit(limit).all()]


def acknowledge_alert_event(db: Session, event_id: int) -> AlertEventRead | None:
    row = db.get(AlertEvent, event_id)
    if row is None:
        return None
    row.acknowledged = True
    db.commit()
    db.refresh(row)
    return AlertEventRead.model_validate(row)


def _threshold_json_payload(
    event_type: str, summary: HighLevelSummary, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": event_type,
        "banner": summary.banner,
        "banner_text": summary.banner_text,
        "important_down": summary.important_down,
        "important_total": summary.important_total,
        "important_up": summary.important_up,
        "internet_health": summary.internet_health,
        "internet_summary": summary.internet_summary,
        "timestamp": summary.timestamp.isoformat(),
    }
    if extra:
        payload.update(extra)
    return payload


async def _send_threshold_webhook(
    db: Session,
    settings: AlertSettings,
    summary: HighLevelSummary,
    event_type: str,
    message: str,
    severity: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = _threshold_json_payload(event_type, summary, extra)
    record_alert_event(
        db,
        event_type=event_type,
        severity=severity,
        message=message,
        payload=payload,
    )
    if not settings.enabled or not settings.webhook_url:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        body = build_webhook_payload(settings, summary)
        body["event"] = event_type
        body["threshold_message"] = message
        if extra:
            body.update(extra)
        response = await client.post(settings.webhook_url, json=body)
        response.raise_for_status()


async def evaluate_threshold_alerts(db: Session, summary: HighLevelSummary) -> None:
    settings = get_alert_settings(db)
    state = _get_alert_state(db)

    down_active = (
        settings.threshold_important_down > 0
        and summary.important_down >= settings.threshold_important_down
    )
    if down_active and not state.get("threshold_down_active"):
        message = (
            f"{summary.important_down} important device(s) down "
            f"(threshold ≥ {settings.threshold_important_down})"
        )
        try:
            await _send_threshold_webhook(
                db,
                settings,
                summary,
                "threshold_important_down",
                message,
                "critical",
                {"threshold": settings.threshold_important_down},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Threshold alert failed: %s", exc)
    state["threshold_down_active"] = down_active

    internet_active = (
        settings.threshold_internet_degraded
        and summary.internet_health not in {"ok"}
    )
    if internet_active and not state.get("threshold_internet_active"):
        message = f"Internet health degraded: {summary.internet_summary}"
        try:
            await _send_threshold_webhook(
                db,
                settings,
                summary,
                "threshold_internet_degraded",
                message,
                "warning",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Threshold alert failed: %s", exc)
    state["threshold_internet_active"] = internet_active

    _set_alert_state(db, state)


async def maybe_send_banner_alert(db: Session, summary: HighLevelSummary) -> None:
    settings = get_alert_settings(db)
    if not settings.enabled or not settings.webhook_url:
        return

    state = _get_alert_state(db)
    last_banner = state.get("last_banner")
    last_sent = state.get("last_sent_at")
    now = datetime.now(UTC)

    if last_banner == summary.banner:
        return

    if last_sent:
        last_dt = datetime.fromisoformat(last_sent)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=UTC)
        if now - last_dt < timedelta(seconds=settings.min_interval_sec):
            return

    try:
        await send_webhook(settings, summary)
        record_alert_event(
            db,
            event_type="banner_change",
            severity="critical" if summary.banner in {"devices_down", "mixed"} else "warning",
            message=summary.banner_text,
            payload=build_json_payload(summary),
        )
        merged = {**state, "last_banner": summary.banner, "last_sent_at": now.isoformat()}
        _set_alert_state(db, merged)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Webhook alert failed: %s", exc)


async def send_test_alert(db: Session) -> AlertTestResult:
    from app.services.aggregation import compute_high_level_summary

    settings = get_alert_settings(db)
    if not settings.webhook_url:
        return AlertTestResult(ok=False, message="Webhook URL is not configured")

    summary = compute_high_level_summary(db)
    try:
        await send_webhook(settings, summary, test=True)
        return AlertTestResult(ok=True, message=f"Test alert sent ({settings.format} format)")
    except Exception as exc:  # noqa: BLE001
        return AlertTestResult(ok=False, message=str(exc))