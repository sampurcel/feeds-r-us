from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.ingestion import FeedIngestionService
from app.services.retention import purge_expired_intel

logger = logging.getLogger(__name__)


async def run_ingestion_job() -> None:
    async with SessionLocal() as session:
        service = FeedIngestionService(session)
        await service.run()


async def run_retention_job() -> None:
    async with SessionLocal() as session:
        await purge_expired_intel(session, settings.retention_days)


def create_scheduler() -> AsyncIOScheduler:
    tz = ZoneInfo(settings.scheduler_timezone)
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        run_ingestion_job,
        IntervalTrigger(minutes=settings.ingestion_interval_minutes, timezone=tz),
        id="feed-ingestion",
        replace_existing=True,
    )
    scheduler.add_job(
        run_retention_job,
        IntervalTrigger(hours=24, timezone=tz),
        id="retention-prune",
        replace_existing=True,
    )
    return scheduler
