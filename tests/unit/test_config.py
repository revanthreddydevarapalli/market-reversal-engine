import os

from src.config.settings import AppEnv, get_settings


def test_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_env == AppEnv.TEST
    assert settings.is_test is True
    assert settings.database_url == "sqlite:///:memory:"


def test_settings_defaults_when_env_unset(monkeypatch):
    # Remove vars this test cares about so defaults are exercised;
    # conftest's autouse fixture clears the cache before/after.
    monkeypatch.delenv("APP_NAME", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_name == "market-reversal-engine"
    assert settings.api_port == 8000


def test_get_settings_is_cached():
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
