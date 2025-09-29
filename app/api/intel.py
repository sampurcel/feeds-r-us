from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext, get_current_user, require_roles
from app.db.session import get_db
from app.models import Indicator, IntelItem, IntelSource, UserRole
from app.schemas.common import Message, PaginatedResponse
from app.schemas.intel import IntelItemCreate, IntelItemRead, IntelItemUpdate

router = APIRouter(prefix="/intel", tags=["intel"])


def _build_intel_filters(
    since: datetime | None,
    until: datetime | None,
    feed_id: uuid.UUID | None,
    q: str | None,
    relevance: bool | None,
):
    filters = []
    if since:
        filters.append(IntelItem.discovered_at >= since)
    if until:
        filters.append(IntelItem.discovered_at <= until)
    if q:
        like = f"%{q.lower()}%"
        filters.append(
            func.lower(IntelItem.title).like(like)
            | func.lower(func.coalesce(IntelItem.description, ""))
            .like(like)
        )
    if relevance is True:
        filters.append(func.coalesce(func.json_array_length(IntelItem.org_relevance_tags), 0) > 0)
    if relevance is False:
        filters.append(func.coalesce(func.json_array_length(IntelItem.org_relevance_tags), 0) == 0)
    if feed_id:
        filters.append(
            IntelItem.id.in_(select(IntelSource.intel_item_id).where(IntelSource.feed_id == feed_id))
        )
    return filters


@router.get("", response_model=PaginatedResponse[IntelItemRead])
async def list_intel_items(
    page: int = 1,
    size: int = 50,
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    feed_id: uuid.UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    relevance: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(get_current_user),
) -> PaginatedResponse[IntelItemRead]:
    filters = _build_intel_filters(since, until, feed_id, q, relevance)
    base_query = select(IntelItem).order_by(
        IntelItem.discovered_at.desc().nullslast(), IntelItem.created_at.desc()
    )
    if filters:
        base_query = base_query.where(and_(*filters))
    result = await db.execute(base_query.offset((page - 1) * size).limit(size))
    items = result.scalars().unique().all()

    count_query = select(func.count(IntelItem.id))
    if filters:
        count_query = count_query.where(and_(*filters))
    total = await db.scalar(count_query)

    return PaginatedResponse(
        items=[IntelItemRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        size=size,
    )


@router.get("/{intel_id}", response_model=IntelItemRead)
async def get_intel_item(
    intel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(get_current_user),
) -> IntelItemRead:
    item = await db.get(IntelItem, intel_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intel item not found")
    return IntelItemRead.model_validate(item)


@router.post("", response_model=IntelItemRead, status_code=status.HTTP_201_CREATED)
async def create_intel_item(
    payload: IntelItemCreate,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
) -> IntelItemRead:
    item = IntelItem(**payload.model_dump(exclude={"indicators", "sources"}))
    db.add(item)
    await db.flush()

    for indicator_payload in payload.indicators:
        indicator = Indicator(intel_item_id=item.id, **indicator_payload)
        db.add(indicator)
    for source_payload in payload.sources:
        source = IntelSource(intel_item_id=item.id, **source_payload)
        db.add(source)

    await db.commit()
    await db.refresh(item)
    return IntelItemRead.model_validate(item)


@router.put("/{intel_id}", response_model=IntelItemRead)
async def update_intel_item(
    intel_id: uuid.UUID,
    payload: IntelItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
) -> IntelItemRead:
    item = await db.get(IntelItem, intel_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intel item not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return IntelItemRead.model_validate(item)


@router.delete("/{intel_id}", response_model=Message)
async def delete_intel_item(
    intel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ADMIN)),
) -> Message:
    item = await db.get(IntelItem, intel_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intel item not found")
    await db.delete(item)
    await db.commit()
    return Message(detail="Intel item deleted")
