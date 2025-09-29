from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.models import Base
from app.tasks.scheduler import create_scheduler

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    scheduler = create_scheduler()

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Starting application")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        scheduler.start()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("Stopping application")
        scheduler.shutdown(wait=False)

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
