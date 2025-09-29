from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext, require_roles
from app.db.session import get_db
from app.models import Feed, UserRole
from app.schemas.common import Message, PaginatedResponse
from app.schemas.feed import FeedCreate, FeedRead, FeedUpdate

router = APIRouter(prefix="/feeds", tags=["feeds"])


@router.get("", response_model=PaginatedResponse[FeedRead])
async def list_feeds(
    page: int = 1,
    size: int = 50,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ADMIN)),
) -> PaginatedResponse[FeedRead]:
    query = select(Feed).order_by(Feed.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    feeds = result.scalars().all()
    total = await db.scalar(select(func.count(Feed.id)))
    return PaginatedResponse(
        items=[FeedRead.model_validate(feed) for feed in feeds],
        total=total or 0,
        page=page,
        size=size,
    )


@router.post("", response_model=FeedRead, status_code=status.HTTP_201_CREATED)
async def create_feed(
    payload: FeedCreate,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ADMIN)),
) -> FeedRead:
    feed = Feed(**payload.model_dump())
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    return FeedRead.model_validate(feed)


@router.get("/{feed_id}", response_model=FeedRead)
async def get_feed(
    feed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ADMIN)),
) -> FeedRead:
    feed = await db.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    return FeedRead.model_validate(feed)


@router.put("/{feed_id}", response_model=FeedRead)
async def update_feed(
    feed_id: uuid.UUID,
    payload: FeedUpdate,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ADMIN)),
) -> FeedRead:
    feed = await db.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(feed, key, value)
    await db.commit()
    await db.refresh(feed)
    return FeedRead.model_validate(feed)


@router.delete("/{feed_id}", response_model=Message)
async def delete_feed(
    feed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ADMIN)),
) -> Message:
    feed = await db.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    await db.delete(feed)
    await db.commit()
    return Message(detail="Feed deleted")
