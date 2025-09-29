from __future__ import annotations

from fastapi import APIRouter

from app.api import feeds, intel, newsletters, users

api_router = APIRouter()
api_router.include_router(feeds.router)
api_router.include_router(intel.router)
api_router.include_router(newsletters.router)
api_router.include_router(users.router)
