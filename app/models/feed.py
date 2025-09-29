from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FeedType(str, Enum):
    RSS = "rss"
    ATOM = "atom"
    STIX_TAXII = "stix-taxii"
    JSON = "json"
    SCRAPER = "scraper"


class Feed(Base):
    """Feed definition entity."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    feed_type: Mapped[FeedType] = mapped_column(SqlEnum(FeedType), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule_minutes: Mapped[int] = mapped_column(default=60)
    auth_config: Mapped[dict | None] = mapped_column(JSON, default=None)
    parsing_config: Mapped[dict | None] = mapped_column(JSON, default=None)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(64))
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    intel_sources: Mapped[list["IntelSource"]] = relationship(
        back_populates="feed", cascade="all, delete-orphan"
    )
