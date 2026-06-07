import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.settings import AppSettings
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


def build_webhook_payload(
    settings: AlertSettings, summary: HighLevelSummary, *, test: bool = False
) -> dict[str, Any]:
    if settings.format == "slack":
        return build_slack_payload(summary, test=test)
    return build_json_payload(summary, test=test)


async def send_webhook(
    settings: AlertSettings, summary: HighLevelSummary, *, test: bool = False
) -> None:
    payload = build_webhook_payload(settings, summary, test=test)
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(settings.webhook_url, json=payload)
        response.raise_for_status()


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
        _set_alert_state(
            db,
            {"last_banner": summary.banner, "last_sent_at": now.isoformat()},
        )
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