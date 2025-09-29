from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NewsletterIssue(Base):
    """Newsletter issue stored in the platform."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pdf_blob_path: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    versions: Mapped[list["NewsletterVersion"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan", order_by="NewsletterVersion.created_at"
    )
    entries: Mapped[list["NewsletterIntel"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan", order_by="NewsletterIntel.position"
    )


class NewsletterVersion(Base):
    """Version history for newsletter edits."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("newsletterissue.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    editor: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    issue: Mapped["NewsletterIssue"] = relationship(back_populates="versions")


class NewsletterIntel(Base):
    """Link table between newsletters and intel items."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("newsletterissue.id", ondelete="CASCADE"), nullable=False
    )
    intel_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelitem.id", ondelete="CASCADE"), nullable=False
    )
    section: Mapped[str | None] = mapped_column(String(128))
    position: Mapped[int] = mapped_column(Integer, default=0)

    issue: Mapped["NewsletterIssue"] = relationship(back_populates="entries")
