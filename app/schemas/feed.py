from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.feed import FeedType


class FeedBase(BaseModel):
    name: str = Field(max_length=255)
    feed_type: FeedType
    url: str
    enabled: bool = True
    schedule_minutes: int = Field(default=60, ge=5)
    auth_config: dict | None = None
    parsing_config: dict | None = None


class FeedCreate(FeedBase):
    pass


class FeedUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    enabled: bool | None = None
    schedule_minutes: int | None = Field(default=None, ge=5)
    auth_config: dict | None = None
    parsing_config: dict | None = None


class FeedRead(FeedBase):
    id: uuid.UUID
    last_run_at: datetime | None = None
    last_status: str | None = None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
