"""
Shared SQLAlchemy declarative base.

All ORM models (introduced starting Phase 5 onward, per the build spec's
"Database Design" section) must inherit from `Base` so that a single
`MetaData` object is available to Alembic for autogeneration.

Phase 1 intentionally does not define any domain models yet
(symbols, market_bars, volume_profiles, levels, ...). It only wires the
base + engine + Alembic so later phases can add models without touching
this infrastructure again.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models in the research engine."""
