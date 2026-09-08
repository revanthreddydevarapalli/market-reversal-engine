"""
Trade journal persistence (v1-lite scope).

This is intentionally narrower than the full master-spec journal (no
entry/exit/P&L tracking yet -- that needs a real position lifecycle,
which doesn't exist until Phase 8-equivalent trade-engine work). What
this DOES capture: a timestamped record of "this zone was reached, at
this price, and this was the model's basic option suggestion at that
moment" -- which is the raw material the eventual win/loss tracking
will need, and useful on its own for "did this happen again" review.

ASSUMPTION: one row per (symbol, zone, status) combination is logged at
most once per `JOURNAL_DEDUP_WINDOW_MINUTES` (see journal_service.py)
to avoid spamming duplicate rows every time the frontend polls
/levels/{symbol} while a zone stays REACHED.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    symbol: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(16))  # SUPPORT | RESISTANCE
    status: Mapped[str] = mapped_column(String(16))  # WAITING | NEAR | REACHED

    current_price: Mapped[float] = mapped_column(Float)
    zone_low: Mapped[float] = mapped_column(Float)
    zone_high: Mapped[float] = mapped_column(Float)
    zone_center: Mapped[float] = mapped_column(Float)
    strength_stars: Mapped[int] = mapped_column(Integer)
    timeframes_present: Mapped[list] = mapped_column(JSON)
    level_types_present: Mapped[list] = mapped_column(JSON)

    option_call_put: Mapped[str | None] = mapped_column(String(8), nullable=True)
    option_strike: Mapped[float | None] = mapped_column(Float, nullable=True)
    option_expiration: Mapped[str | None] = mapped_column(String(16), nullable=True)
    option_dte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    option_mid_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    option_otm_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    option_contract_symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    option_status: Mapped[str] = mapped_column(String(32))

    strategy_version: Mapped[str] = mapped_column(String(32))
