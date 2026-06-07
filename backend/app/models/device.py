import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(64), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    important_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    management_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    connector_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    latest_status: Mapped["LatestStatus | None"] = relationship(
        back_populates="device", uselist=False, cascade="all, delete-orphan"
    )


class LatestStatus(Base):
    __tablename__ = "latest_status"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), unique=True)
    overall: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(String(512), default="")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    device: Mapped[Device] = relationship(back_populates="latest_status")