from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable

import feedparser
import httpx
from dateutil import parser as date_parser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Feed, FeedType, Indicator, IntelItem, IntelSource

logger = logging.getLogger(__name__)


class FeedIngestionService:
    """Coordinates feed polling and normalization."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self) -> None:
        result = await self.session.execute(select(Feed).where(Feed.enabled == True))  # noqa: E712
        feeds: Iterable[Feed] = result.scalars().all()
        for feed in feeds:
            try:
                await self._ingest_feed(feed)
                feed.last_status = "success"
                feed.consecutive_failures = 0
            except Exception as exc:  # pragma: no cover - runtime behaviour
                logger.exception("Failed to ingest feed %s", feed.name, exc_info=exc)
                feed.last_status = f"error: {exc}"[:255]
                feed.consecutive_failures += 1
            finally:
                feed.last_run_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def _ingest_feed(self, feed: Feed) -> None:
        logger.info("Ingesting feed %s (%s)", feed.name, feed.feed_type)
        if feed.feed_type in {FeedType.RSS, FeedType.ATOM}:
            await self._ingest_rss(feed)
        elif feed.feed_type == FeedType.JSON:
            await self._ingest_json(feed)
        else:
            logger.info("Feed type %s not yet implemented for %s", feed.feed_type, feed.url)

    async def _ingest_rss(self, feed: Feed) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(feed.url, timeout=15)
            response.raise_for_status()
            parsed = feedparser.parse(response.text)
        for entry in parsed.entries:
            await self._upsert_intel_from_entry(feed, entry)

    async def _ingest_json(self, feed: Feed) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(feed.url, timeout=15)
            response.raise_for_status()
            payload = response.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        for entry in items:
            await self._upsert_intel_from_entry(feed, entry)

    async def _upsert_intel_from_entry(self, feed: Feed, entry: dict | object) -> None:
        data = self._normalize_entry(feed, entry)
        if not data:
            return
        intel = IntelItem(**data["intel"])
        self.session.add(intel)
        await self.session.flush()
        for source_payload in data.get("sources", []):
            source = IntelSource(intel_item_id=intel.id, **source_payload)
            self.session.add(source)
        for indicator_payload in data.get("indicators", []):
            indicator = Indicator(intel_item_id=intel.id, **indicator_payload)
            self.session.add(indicator)

    def _normalize_entry(self, feed: Feed, entry: dict | object) -> dict | None:
        if isinstance(entry, dict):
            title = entry.get("title") or entry.get("headline")
            description = entry.get("description") or entry.get("summary")
            published = entry.get("published") or entry.get("date")
            link = entry.get("link") or entry.get("url")
        else:
            title = getattr(entry, "title", None)
            description = getattr(entry, "summary", None)
            published = getattr(entry, "published", None)
            link = getattr(entry, "link", None)
        if not title:
            return None
        published_at = self._parse_datetime(published)
        intel_payload = {
            "title": title,
            "summary": description[:1024] if isinstance(description, str) else None,
            "description": description if isinstance(description, str) else None,
            "published_at": published_at,
            "discovered_at": datetime.now(timezone.utc),
            "attack_techniques": [],
            "cve_ids": [],
            "org_relevance_tags": [],
        }
        sources = [
            {
                "source_name": feed.name,
                "url": link,
                "fetched_at": datetime.now(timezone.utc),
                "feed_id": feed.id,
            }
        ]
        return {"intel": intel_payload, "sources": sources, "indicators": []}

    def _parse_datetime(self, value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = date_parser.parse(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return None
        return None
