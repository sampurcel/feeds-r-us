from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IntelItem, NewsletterIssue, NewsletterVersion

logger = logging.getLogger(__name__)


async def generate_weekly_draft(
    session: AsyncSession,
    issue: NewsletterIssue,
    days: int = 7,
) -> NewsletterVersion:
    """Create a simple draft newsletter from recent intel items."""

    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(IntelItem)
        .where(IntelItem.discovered_at >= since)
        .order_by(IntelItem.discovered_at.desc())
        .limit(20)
    )
    items: Sequence[IntelItem] = result.scalars().all()
    sections = [
        f"- {item.title}" + (f" (Threat Actor: {item.threat_actor})" if item.threat_actor else "")
        for item in items
    ]
    body = "\n".join(sections) or "No significant events captured this week."
    version = NewsletterVersion(
        issue_id=issue.id,
        version_number=len(issue.versions) + 1,
        editor="auto",
        content=f"Weekly intelligence summary:\n{body}",
    )
    session.add(version)
    await session.commit()
    await session.refresh(issue)
    logger.info("Generated AI draft for issue %s with %d items", issue.slug, len(items))
    return version
