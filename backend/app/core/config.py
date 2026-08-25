"""Application configuration.

Every secret and environment-specific value is read from the environment (or a
local .env file).  Nothing here is ever exposed to the frontend bundle.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Nookr"
    environment: str = "development"

    # The cooperative closes its books at local midnight, not at midnight UTC.
    # Any IANA timezone name; requires the 'tzdata' package on Windows.
    cooperative_timezone: str = "Asia/Kolkata"

    # --- database -----------------------------------------------------------
    # PostgreSQL is the production target.  SQLite is the default so the demo
    # runs on any machine with zero external services, which is a hard
    # requirement for live judging.
    database_url: str = Field(default="sqlite:///./nookr.db")

    # --- auth ---------------------------------------------------------------
    jwt_secret: str = Field(default="dev-only-insecure-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    # --- cors ---------------------------------------------------------------
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
        ]
    )

    # --- optional LLM -------------------------------------------------------
    ai_api_key: str = ""
    ai_model: str = "claude-sonnet-5"
    ai_base_url: str = "https://api.anthropic.com"
    ai_timeout_seconds: float = 12.0

    # --- demo ---------------------------------------------------------------
    demo_password: str = "demo1234"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def llm_enabled(self) -> bool:
        return bool(self.ai_api_key.strip())

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def startup_warnings(self) -> list[str]:
        """Non-fatal configuration problems surfaced at boot and on /health."""
        warnings: list[str] = []
        if self.jwt_secret == "dev-only-insecure-secret-change-me":
            warnings.append(
                "JWT_SECRET is using the built-in development default. "
                "Set JWT_SECRET before deploying."
            )
        if self.environment != "development" and self.is_sqlite:
            warnings.append(
                "DATABASE_URL points at SQLite outside development. "
                "Set a PostgreSQL DATABASE_URL for deployed environments."
            )
        return warnings


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
