"""Settings for the backend service, loaded from environment variables (and an optional
.env file for local dev — see service/.env.example). Every field has a safe local-dev
default so `service/app/main.py` boots against the same docker-compose Postgres the
existing pipeline/postgis/ track already uses, with zero required configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://transit:transit@localhost:5432/transit"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Auth (wired up starting Phase 2)
    jwt_secret_key: str = "dev-insecure-secret-change-me"
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 7

    # LLM agent (wired up starting Phase 4) — provider-agnostic, selected at runtime
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Geocoding (wired up starting Phase 3) — Nominatim is the default (free, no key
    # required); Mapbox is a config-only swap proving the GeocodingProvider abstraction
    # actually swaps providers, not just describes doing so.
    geocoder_provider: str = "nominatim"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = "gtfs-transit-platform/0.1"
    mapbox_api_key: str | None = None

    rate_limit_default_per_min: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
