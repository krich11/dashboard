from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExternalReachabilityResult(Base):
    __tablename__ = "external_reachability_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ipv4_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    ipv6_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    ipv4_targets: Mapped[list] = mapped_column(JSON, default=list)
    ipv6_targets: Mapped[list] = mapped_column(JSON, default=list)
    overall: Mapped[str] = mapped_column(String(32), default="unknown")
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)