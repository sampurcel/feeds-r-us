from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.models.user import UserRole


class UserRead(BaseModel):
    id: uuid.UUID
    user_object_id: str
    email: str
    display_name: str | None = None
    role: UserRole

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: UserRole | None = None
