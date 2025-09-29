from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IntelItem

logger = logging.getLogger(__name__)


async def purge_expired_intel(session: AsyncSession, retention_days: int) -> int:
    """Delete intel items older than retention window."""

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    stmt = delete(IntelItem).where(IntelItem.discovered_at < cutoff)
    result = await session.execute(stmt)
    deleted = result.rowcount or 0
    await session.commit()
    logger.info("Purged %s intel items older than %s", deleted, cutoff)
    return deleted
