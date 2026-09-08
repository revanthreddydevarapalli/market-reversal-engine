"""
FastAPI application entrypoint.

Serves the JSON API (health, symbols, levels, journal) AND the static
frontend (frontend/index.html) from the same origin, so the browser
never hits a CORS wall talking to this same server.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.routers import health, journal, levels, symbols
from src.config.settings import get_settings
from src.database.base import Base
from src.database.session import engine

# Ensure all model modules are imported so their tables register on
# Base.metadata before create_all/migrations run.
from src.models import journal_entry  # noqa: F401

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Dev convenience so the journal works immediately without a
    # separate `alembic upgrade head` step. Alembic (migrations/)
    # remains the source of truth for schema changes going forward --
    # this is a safety net, not a replacement for migrations.
    # Silently no-ops (with a printed warning) if the DB isn't
    # reachable yet, so a missing/misconfigured DB doesn't crash the
    # whole app -- /levels still works, journal logging just won't
    # persist until the DB is available.
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] WARNING: could not create/verify DB tables: {exc}")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "US Market Higher-Timeframe Volume Profile Reversal Engine -- "
            "research/backend API. This is a research tool: outputs reflect "
            "measured historical behavior, not guarantees of future results."
        ),
        version="0.1.0",
        lifespan=_lifespan,
    )

    app.include_router(health.router)
    app.include_router(levels.router)
    app.include_router(symbols.router)
    app.include_router(journal.router)

    # Static frontend, mounted last so it only catches requests that
    # don't match one of the API routes above (e.g. "/", "/index.html").
    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
