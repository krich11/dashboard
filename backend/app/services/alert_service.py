import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app.models.settings import AppSettings
from app.schemas.settings import AlertSettings
from app.schemas.status import HighLevelSummary

logger = logging.getLogger(__name__)


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

    payload = {
        "event": "banner_change",
        "banner": summary.banner,
        "banner_text": summary.banner_text,
        "important_down": summary.important_down,
        "important_total": summary.important_total,
        "internet_health": summary.internet_health,
        "timestamp": summary.timestamp.isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(settings.webhook_url, json=payload)
            response.raise_for_status()
        _set_alert_state(
            db,
            {"last_banner": summary.banner, "last_sent_at": now.isoformat()},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Webhook alert failed: %s", exc)