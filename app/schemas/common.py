from __future__ import annotations

from datetime import datetime
from typing import Generic, Iterable, Sequence, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic pagination wrapper."""

    items: Sequence[T]
    total: int
    page: int = Field(default=1, ge=1)
    size: int = Field(default=50, ge=1)


class Message(BaseModel):
    """Simple message payload."""

    detail: str


class TimestampMixin(BaseModel):
    """Mixin to expose created/updated fields."""

    created_at: datetime
    updated_at: datetime | None = None


class AuditFields(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None
