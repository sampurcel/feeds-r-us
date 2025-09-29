from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext, get_current_user, require_roles
from app.db.session import get_db
from app.models import IntelItem, NewsletterIntel, NewsletterIssue, NewsletterVersion, UserRole
from app.schemas.common import Message, PaginatedResponse
from app.schemas.newsletter import (
    NewsletterAttachRequest,
    NewsletterIssueCreate,
    NewsletterIssueRead,
    NewsletterIssueUpdate,
    NewsletterPublishRequest,
)

router = APIRouter(prefix="/newsletters", tags=["newsletters"])


def _serialize_issue(issue: NewsletterIssue) -> NewsletterIssueRead:
    return NewsletterIssueRead.model_validate(issue)


@router.get("", response_model=PaginatedResponse[NewsletterIssueRead])
async def list_newsletters(
    page: int = 1,
    size: int = 50,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(get_current_user),
) -> PaginatedResponse[NewsletterIssueRead]:
    query = (
        select(NewsletterIssue)
        .order_by(NewsletterIssue.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    issues = result.scalars().unique().all()
    total = await db.scalar(select(func.count(NewsletterIssue.id)))
    return PaginatedResponse(
        items=[_serialize_issue(issue) for issue in issues],
        total=total or 0,
        page=page,
        size=size,
    )


@router.post("", response_model=NewsletterIssueRead, status_code=status.HTTP_201_CREATED)
async def create_newsletter(
    payload: NewsletterIssueCreate,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
) -> NewsletterIssueRead:
    issue = NewsletterIssue(
        slug=payload.slug,
        title=payload.title,
        status=payload.status,
        scheduled_for=payload.scheduled_for,
    )
    db.add(issue)
    await db.flush()

    if payload.initial_content:
        version = NewsletterVersion(
            issue_id=issue.id,
            version_number=1,
            editor=payload.editor or "system",
            content=payload.initial_content,
        )
        db.add(version)

    await db.commit()
    await db.refresh(issue)
    return _serialize_issue(issue)


@router.get("/{issue_id}", response_model=NewsletterIssueRead)
async def get_newsletter(
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(get_current_user),
) -> NewsletterIssueRead:
    issue = await db.get(NewsletterIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found")
    return _serialize_issue(issue)


@router.put("/{issue_id}", response_model=NewsletterIssueRead)
async def update_newsletter(
    issue_id: uuid.UUID,
    payload: NewsletterIssueUpdate,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
) -> NewsletterIssueRead:
    issue = await db.get(NewsletterIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(issue, key, value)
    await db.commit()
    await db.refresh(issue)
    return _serialize_issue(issue)


@router.post("/{issue_id}/publish", response_model=NewsletterIssueRead)
async def publish_newsletter(
    issue_id: uuid.UUID,
    payload: NewsletterPublishRequest,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
) -> NewsletterIssueRead:
    issue = await db.get(NewsletterIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found")

    latest_version_query = (
        select(func.max(NewsletterVersion.version_number)).where(NewsletterVersion.issue_id == issue_id)
    )
    latest_version = await db.scalar(latest_version_query)
    version_number = (latest_version or 0) + 1

    version = NewsletterVersion(
        issue_id=issue_id,
        version_number=version_number,
        editor=payload.editor,
        content=payload.content,
    )
    db.add(version)

    issue.status = "published"
    issue.published_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(issue)
    return _serialize_issue(issue)


@router.post("/{issue_id}/entries", response_model=Message)
async def attach_intel_to_newsletter(
    issue_id: uuid.UUID,
    payload: NewsletterAttachRequest,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
) -> Message:
    issue = await db.get(NewsletterIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found")

    intel_ids = payload.intel_ids
    if not intel_ids:
        await db.execute(NewsletterIntel.__table__.delete().where(NewsletterIntel.issue_id == issue_id))
        await db.commit()
        return Message(detail="Newsletter intel updated")

    result = await db.execute(select(IntelItem.id).where(IntelItem.id.in_(intel_ids)))
    available_ids = set(result.scalars().all())
    missing = set(intel_ids) - available_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown intel IDs: {', '.join(map(str, missing))}",
        )

    await db.execute(NewsletterIntel.__table__.delete().where(NewsletterIntel.issue_id == issue_id))

    section_map = payload.section_map or {}
    for position, intel_id in enumerate(intel_ids):
        section = section_map.get(intel_id) if intel_id in section_map else section_map.get(str(intel_id))
        entry = NewsletterIntel(
            issue_id=issue_id,
            intel_item_id=intel_id,
            section=section,
            position=position,
        )
        db.add(entry)

    await db.commit()
    return Message(detail="Newsletter intel updated")
