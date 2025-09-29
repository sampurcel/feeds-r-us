from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext, get_current_user, require_roles
from app.db.session import get_db
from app.models import UserProfile, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(context: AuthContext = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(context.user)


@router.get("", response_model=PaginatedResponse[UserRead])
async def list_users(
    page: int = 1,
    size: int = 50,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ADMIN)),
) -> PaginatedResponse[UserRead]:
    query = (
        select(UserProfile)
        .order_by(UserProfile.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    users = result.scalars().all()
    total = await db.scalar(select(func.count(UserProfile.id)))
    return PaginatedResponse(
        items=[UserRead.model_validate(user) for user in users],
        total=total or 0,
        page=page,
        size=size,
    )


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ADMIN)),
) -> UserRead:
    user = await db.get(UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return UserRead.model_validate(user)
