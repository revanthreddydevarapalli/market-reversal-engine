"""
Trade journal service. Two responsibilities:
  1. log_reached_zones -- called after analyze_symbol(); persists any
     zone currently at status REACHED, deduplicated so repeated polling
     doesn't spam duplicate rows for the same still-active signal.
  2. get_journal_entries -- read back logged entries, optionally
     filtered by symbol.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config.strategy_params import StrategyParameters
from src.models.journal_entry import JournalEntry
from src.services.reversal_service import SymbolAnalysis, ZoneAnalysis

# ASSUMPTION: a given (symbol, zone, status) combination is only logged
# once per this window, so a frontend polling /levels/{symbol} every
# few seconds while a zone stays REACHED doesn't create a new row each
# time. Tune as needed once real usage patterns are known.
JOURNAL_DEDUP_WINDOW_MINUTES = 60


def _zone_key_matches(entry: JournalEntry, symbol: str, zone: ZoneAnalysis) -> bool:
    return (
        entry.symbol == symbol
        and entry.side == zone.side
        and abs(entry.zone_low - zone.zone.lower) < 1e-6
        and abs(entry.zone_high - zone.zone.upper) < 1e-6
    )


def log_reached_zones(
    db: Session, analysis: SymbolAnalysis, params: StrategyParameters
) -> list[JournalEntry]:
    """Persist any REACHED zone from this analysis, skipping ones
    already logged for the same symbol/zone within the dedup window.
    Returns the newly-created entries (empty list if everything was a
    duplicate or nothing was REACHED)."""
    all_zones = analysis.support_zones + analysis.resistance_zones
    reached = [z for z in all_zones if z.status == "REACHED"]
    if not reached:
        return []

    cutoff = datetime.now(UTC) - timedelta(minutes=JOURNAL_DEDUP_WINDOW_MINUTES)
    recent_entries = db.execute(
        select(JournalEntry).where(
            JournalEntry.symbol == analysis.symbol, JournalEntry.created_at >= cutoff
        )
    ).scalars().all()

    new_entries: list[JournalEntry] = []
    for zone in reached:
        if any(_zone_key_matches(existing, analysis.symbol, zone) for existing in recent_entries):
            continue

        option = zone.option_pick
        entry = JournalEntry(
            created_at=datetime.now(UTC),
            symbol=analysis.symbol,
            side=zone.side,
            status=zone.status,
            current_price=analysis.current_price,
            zone_low=zone.zone.lower,
            zone_high=zone.zone.upper,
            zone_center=zone.zone.center,
            strength_stars=zone.zone.strength_stars,
            timeframes_present=sorted(zone.zone.timeframes_present),
            level_types_present=sorted(zone.zone.level_types_present),
            option_call_put=option.contract.call_put if option else None,
            option_strike=option.contract.strike if option else None,
            option_expiration=option.contract.expiration.date().isoformat() if option else None,
            option_dte=option.dte if option else None,
            option_mid_price=option.mid_price if option else None,
            option_otm_pct=option.otm_pct if option else None,
            option_contract_symbol=option.contract.contract_symbol if option else None,
            option_status=zone.option_status,
            strategy_version=params.version,
        )
        db.add(entry)
        new_entries.append(entry)

    if new_entries:
        db.commit()
        for entry in new_entries:
            db.refresh(entry)

    return new_entries


def get_journal_entries(db: Session, symbol: str | None = None, limit: int = 100) -> list[JournalEntry]:
    query = select(JournalEntry).order_by(JournalEntry.created_at.desc()).limit(limit)
    if symbol:
        query = query.where(JournalEntry.symbol == symbol.upper())
    return list(db.execute(query).scalars().all())
