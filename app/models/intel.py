from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class IntelItem(Base):
    """Normalized intelligence event."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(1024))
    description: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    severity: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(Float)
    threat_actor: Mapped[str | None] = mapped_column(String(255))
    campaign: Mapped[str | None] = mapped_column(String(255))
    attack_techniques: Mapped[list[str]] = mapped_column(JSON, default=list)
    cve_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    org_relevance_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelitem.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sources: Mapped[list["IntelSource"]] = relationship(
        back_populates="intel_item", cascade="all, delete-orphan"
    )
    indicators: Mapped[list["Indicator"]] = relationship(
        back_populates="intel_item", cascade="all, delete-orphan"
    )


class IntelSource(Base):
    """Source attribution for an intel item."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    intel_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelitem.id", ondelete="CASCADE"), nullable=False
    )
    feed_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feed.id", ondelete="SET NULL")
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    excerpt: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict | None] = mapped_column(JSON, default=None)

    intel_item: Mapped["IntelItem"] = relationship(back_populates="sources")
    feed: Mapped["Feed" | None] = relationship(back_populates="intel_sources")


class Indicator(Base):
    """Indicator of compromise associated with an intel item."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    intel_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelitem.id", ondelete="CASCADE"), nullable=False
    )
    indicator_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(String(512), nullable=False)
    reputation: Mapped[str | None] = mapped_column(String(64))
    context: Mapped[dict | None] = mapped_column(JSON, default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    intel_item: Mapped["IntelItem"] = relationship(back_populates="indicators")
