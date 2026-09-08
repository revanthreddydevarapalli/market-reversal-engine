"""
Central application configuration.

Design principle (see project CLAUDE.md / build spec section 41):
strategy and methodology constants must never be scattered through the
codebase. Phase 1 only introduces *infrastructure* settings (app, API,
database, logging). Strategy/methodology parameters (value area %,
binning method, HVN/LVN thresholds, cluster tolerance, interaction
tolerance, target percentages, invalidation rules, minimum sample size,
regime weights, etc.) belong to a separate, versioned
`StrategyParameters` model that will be introduced in later phases
(and persisted to the `strategy_parameters` table so every backtest run
can record exactly which parameter set produced it). Do not add
strategy constants here.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Infrastructure-level settings, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_env: AppEnv = Field(default=AppEnv.DEVELOPMENT, alias="APP_ENV")
    app_name: str = Field(default="market-reversal-engine", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Database ---
    # Default points at a local Postgres for developer convenience. Tests
    # override this (see tests/unit/conftest usage) to avoid requiring a
    # live database just to run the unit test suite.
    database_url: str = Field(
        default="postgresql+psycopg2://reversal:reversal@localhost:5432/reversal_engine",
        alias="DATABASE_URL",
    )

    # --- API ---
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # --- Data providers (v1-lite) ---
    # Base URL of a separately-running MrChartist/tradingview-scraper
    # instance (its own uvicorn process/container). Do not point this at
    # the same port as this app's own API.
    tradingview_scraper_base_url: str = Field(
        default="http://localhost:8100", alias="TRADINGVIEW_SCRAPER_BASE_URL"
    )

    @property
    def is_test(self) -> bool:
        return self.app_env == AppEnv.TEST


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor.

    Using a function (rather than a module-level singleton) makes it
    straightforward to override settings in tests via
    `get_settings.cache_clear()` + environment variable patching, or via
    FastAPI's dependency-override mechanism.
    """
    return Settings()
