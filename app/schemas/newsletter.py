from __future__ import annotations

import uuid
from datetime import datetime
from typing import Mapping, Sequence

from pydantic import BaseModel, Field


class NewsletterEntry(BaseModel):
    id: uuid.UUID
    intel_item_id: uuid.UUID
    section: str | None = None

    class Config:
        from_attributes = True


class NewsletterVersionRead(BaseModel):
    id: uuid.UUID
    version_number: int
    editor: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class NewsletterIssueBase(BaseModel):
    slug: str = Field(max_length=128)
    title: str = Field(max_length=255)
    status: str = Field(default="draft")
    scheduled_for: datetime | None = None


class NewsletterIssueCreate(NewsletterIssueBase):
    initial_content: str | None = None
    editor: str | None = None


class NewsletterIssueUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    scheduled_for: datetime | None = None
    pdf_blob_path: str | None = None


class NewsletterPublishRequest(BaseModel):
    editor: str
    content: str
    section_order: list[str] | None = None


class NewsletterAttachRequest(BaseModel):
    intel_ids: list[uuid.UUID]
    section_map: Mapping[uuid.UUID, str] | None = None


class NewsletterIssueRead(NewsletterIssueBase):
    id: uuid.UUID
    published_at: datetime | None = None
    pdf_blob_path: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    versions: Sequence[NewsletterVersionRead] = ()
    entries: Sequence[NewsletterEntry] = ()

    class Config:
        from_attributes = True
