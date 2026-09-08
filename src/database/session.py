"""
Database engine and session management.

Kept deliberately thin: engine creation reads the connection string from
`Settings`, and `get_db` is a generator-style dependency FastAPI routes
can use with `Depends(get_db)`. Domain/analytics code (volume_profile,
levels, regime, scoring, backtesting) must not import from this module
directly -- persistence should be mediated through the `services` layer
so the analytics engine stays testable without a database.
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import get_settings


def build_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine.

    `database_url` can be supplied explicitly (used by tests to point at
    an ephemeral SQLite database) instead of always reading from
    `Settings`, so this function stays reusable outside the app context.
    """
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


# Module-level engine/session factory used by the running application.
# (Deferred settings read: constructing this at import time is fine
# because `get_settings()` is cheap and cached.)
engine: Engine = build_engine()
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
