from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Threat Intel Platform"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    alembic_ini_path: str = "alembic.ini"
    allowed_audiences: List[str] = []
    tenant_id: str = ""
    client_id: str = ""
    authority_host: str = "https://login.microsoftonline.com"
    jwks_cache_ttl: int = 3600
    scheduler_timezone: str = "UTC"
    ingestion_interval_minutes: int = 60
    retention_days: int = 31

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


settings = get_settings()
