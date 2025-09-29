from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, Field


class IndicatorRead(BaseModel):
    id: uuid.UUID
    indicator_type: str
    value: str
    reputation: str | None = None
    context: dict | None = None
    last_seen_at: datetime | None = None

    class Config:
        from_attributes = True


class IntelSourceRead(BaseModel):
    id: uuid.UUID
    source_name: str
    url: str | None = None
    fetched_at: datetime | None = None
    feed_id: uuid.UUID | None = None
    excerpt: str | None = None

    class Config:
        from_attributes = True


class IntelItemBase(BaseModel):
    title: str = Field(max_length=512)
    summary: str | None = Field(default=None, max_length=1024)
    description: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime | None = None
    severity: str | None = None
    status: str | None = None
    confidence: float | None = None
    threat_actor: str | None = None
    campaign: str | None = None
    attack_techniques: list[str] = Field(default_factory=list)
    cve_ids: list[str] = Field(default_factory=list)
    org_relevance_tags: list[str] = Field(default_factory=list)


class IntelItemCreate(IntelItemBase):
    indicators: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)


class IntelItemUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    confidence: float | None = None
    threat_actor: str | None = None
    campaign: str | None = None
    attack_techniques: list[str] | None = None
    cve_ids: list[str] | None = None
    org_relevance_tags: list[str] | None = None


class IntelItemRead(IntelItemBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None
    merged_into_id: uuid.UUID | None = None
    sources: Sequence[IntelSourceRead] = ()
    indicators: Sequence[IndicatorRead] = ()

    class Config:
        from_attributes = True
