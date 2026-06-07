from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.collectors.external_reachability import ExternalReachabilityMonitor
from app.collectors.mock import MockConnector
from app.config import get_settings
from app.db.session import SessionLocal
from app.models.device import Device, LatestStatus
from app.services.settings_service import get_collector_settings


@dataclass
class DeviceBackoffState:
    failures: int = 0
    next_poll_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    circuit_open: bool = False


class CollectorService:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self._backoff: dict[str, DeviceBackoffState] = {}
        self._semaphore: asyncio.Semaphore | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        settings = get_settings()
        self._semaphore = asyncio.Semaphore(settings.collector_concurrency)
        self.scheduler.add_job(self._poll_devices_job, "interval", seconds=settings.collector_interval_sec)
        self.scheduler.add_job(
            self._reachability_job,
            "interval",
            seconds=settings.reachability_interval_sec,
        )
        self.scheduler.start()
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        self.scheduler.shutdown(wait=False)
        self._running = False

    async def _reachability_job(self) -> None:
        db = SessionLocal()
        try:
            monitor = ExternalReachabilityMonitor(db)
            await monitor.run_once()
        finally:
            db.close()

    async def _poll_devices_job(self) -> None:
        db = SessionLocal()
        try:
            devices = db.query(Device).all()
            now = datetime.now(UTC)
            due = [
                d
                for d in devices
                if self._backoff.get(d.id, DeviceBackoffState()).next_poll_at <= now
                and not self._backoff.get(d.id, DeviceBackoffState()).circuit_open
            ]
            if not due:
                return
            await asyncio.gather(*(self._poll_one(db, device) for device in due))
            db.commit()
        finally:
            db.close()

    async def _poll_one(self, db: Session, device: Device) -> None:
        settings = get_settings()
        collector = get_collector_settings(db)
        assert self._semaphore is not None
        async with self._semaphore:
            connector = MockConnector(db)
            state = self._backoff.setdefault(device.id, DeviceBackoffState())
            try:
                status = await connector.poll(device.id)
                existing = db.query(LatestStatus).filter(LatestStatus.device_id == device.id).first()
                if existing:
                    existing.overall = status.overall
                    existing.message = status.message
                    existing.metrics = status.metrics
                    existing.details = status.details
                    existing.timestamp = status.timestamp.replace(tzinfo=None)
                else:
                    db.add(
                        LatestStatus(
                            device_id=device.id,
                            overall=status.overall,
                            message=status.message,
                            metrics=status.metrics,
                            details=status.details,
                            timestamp=status.timestamp.replace(tzinfo=None),
                        )
                    )
                state.failures = 0
                state.circuit_open = False
                state.next_poll_at = datetime.now(UTC) + timedelta(
                    seconds=collector.interval_sec
                )
            except Exception as exc:  # noqa: BLE001
                state.failures += 1
                backoff = min(
                    collector.default_backoff_sec * state.failures,
                    collector.max_backoff_sec,
                )
                state.next_poll_at = datetime.now(UTC) + timedelta(seconds=backoff)
                if state.failures >= collector.circuit_breaker_threshold:
                    state.circuit_open = True
                existing = db.query(LatestStatus).filter(LatestStatus.device_id == device.id).first()
                if existing:
                    existing.overall = "unknown"
                    existing.message = f"Collector error: {exc}"
                    existing.timestamp = datetime.now(UTC).replace(tzinfo=None)


collector_service = CollectorService()