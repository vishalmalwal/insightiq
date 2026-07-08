"""Application configuration, loaded from environment (Pydantic Settings v2)."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central, typed settings object. Never log secrets held here."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "InsightIQ"
    environment: Literal["local", "ci", "staging", "production"] = "local"
    log_level: str = "INFO"
    log_json: bool = False  # set True in deployed environments

    # --- API ---
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Access boundary (project-scoped soft gate) ---
    # Single shared secret gates write/LLM actions. When unset, the app is fully
    # open (good for the public sample-data demo). Isolation is enforced at the
    # project_id level, so swapping this for real per-user auth is a middleware
    # change, NOT a schema migration. No users/sessions model exists by design.
    app_shared_secret: str | None = None

    # --- App metadata database (Postgres; Neon in deploy) ---
    database_url: str = "postgresql+psycopg://insightiq:insightiq@localhost:5432/insightiq"

    # --- Analytics storage (DuckDB) + object-storage backend ---
    storage_backend: Literal["local", "r2"] = "local"
    duckdb_dir: str = "./data/duckdb"          # local working/cache dir
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None

    # --- LLM provider ---
    # 'mock' keeps tests/CI free and quota-safe. 'gemini' is the $0 free-tier
    # default for deploy. 'anthropic' is the optional bring-your-own-paid-key path.
    llm_provider: Literal["mock", "gemini", "anthropic"] = "mock"

    # Gemini (free tier). Model ids are env-overridable; verify current ids and
    # free-tier RPM/RPD limits in Google AI Studio — they change without notice.
    # As of 2026-07: gemini-3-flash / gemini-3.5-flash (newer) and
    # gemini-3.1-flash-lite (most cost-efficient) are current.
    google_api_key: str | None = None
    llm_model_planner: str = "gemini-3-flash"          # planner + SQL generation
    llm_model_cheap: str = "gemini-3.1-flash-lite"     # captions + chart tie-breaks

    # Anthropic (optional paid alt).
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    # --- Secrets ---
    # 32-byte urlsafe base64 Fernet key to encrypt stored client DB creds at rest.
    credentials_encryption_key: str | None = None

    # --- Safety limits (executor) ---
    sql_statement_timeout_ms: int = 15_000
    sql_row_limit: int = 10_000
    sql_max_result_bytes: int = 5_000_000

    # --- LLM request queue (Phase 3; sized for free-tier rate limits) ---
    llm_max_rpm: int = 12               # token-bucket refill; tune to live quota
    llm_max_retries_on_429: int = 5

    @property
    def is_deployed(self) -> bool:
        return self.environment in ("staging", "production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
