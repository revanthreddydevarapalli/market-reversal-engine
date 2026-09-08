"""
Shared pytest fixtures.

Phase 1 has no domain models yet, so these fixtures only cover
infrastructure: forcing the app into APP_ENV=test with an isolated
SQLite database so `pytest` never requires a live Postgres instance,
and a FastAPI TestClient for API tests.
"""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from src.config.settings import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None, None, None]:
    """Ensure each test sees settings derived from the current environment."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    from src.api.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
