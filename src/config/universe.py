"""
The tracked symbol universe. Kept in one place (per CLAUDE.md principle
#3 extended to the symbol list) so it's not scattered across the
frontend, API, and services. Exposed via GET /symbols so the frontend
can offer a search/autocomplete instead of requiring the user to type
an exact ticker.

ASSUMPTION: this is a flat, manually-curated list for v1-lite. Future
support for index membership (S&P 500, Nasdaq 100, etc.) or a
user-editable watchlist (persisted, per the original master spec) is
deferred -- see CLAUDE.md.
"""

from __future__ import annotations

from pydantic import BaseModel


class UniverseSymbol(BaseModel):
    symbol: str
    name: str
    asset_class: str  # "EQUITY" | "FUTURE"


EQUITY_UNIVERSE: list[UniverseSymbol] = [
    UniverseSymbol(symbol="AAPL", name="Apple Inc.", asset_class="EQUITY"),
    UniverseSymbol(symbol="NVDA", name="NVIDIA Corporation", asset_class="EQUITY"),
    UniverseSymbol(symbol="MSFT", name="Microsoft Corporation", asset_class="EQUITY"),
    UniverseSymbol(symbol="AMZN", name="Amazon.com, Inc.", asset_class="EQUITY"),
    UniverseSymbol(symbol="META", name="Meta Platforms, Inc.", asset_class="EQUITY"),
    UniverseSymbol(symbol="TSLA", name="Tesla, Inc.", asset_class="EQUITY"),
    UniverseSymbol(symbol="GOOGL", name="Alphabet Inc.", asset_class="EQUITY"),
    UniverseSymbol(symbol="AMD", name="Advanced Micro Devices, Inc.", asset_class="EQUITY"),
    UniverseSymbol(symbol="AVGO", name="Broadcom Inc.", asset_class="EQUITY"),
    UniverseSymbol(symbol="NFLX", name="Netflix, Inc.", asset_class="EQUITY"),
]

# NOTE: futures/index symbols are part of the original master spec's
# market-regime engine (ES/NQ/YM/RTY), which is not implemented yet in
# this v1-lite build. Listed here so the universe config is complete
# and /symbols can distinguish asset classes once regime support lands,
# but /levels/{symbol} does not yet meaningfully support these.
FUTURES_UNIVERSE: list[UniverseSymbol] = [
    UniverseSymbol(symbol="ES", name="E-mini S&P 500", asset_class="FUTURE"),
    UniverseSymbol(symbol="NQ", name="E-mini Nasdaq-100", asset_class="FUTURE"),
    UniverseSymbol(symbol="YM", name="E-mini Dow", asset_class="FUTURE"),
    UniverseSymbol(symbol="RTY", name="E-mini Russell 2000", asset_class="FUTURE"),
]

FULL_UNIVERSE: list[UniverseSymbol] = EQUITY_UNIVERSE + FUTURES_UNIVERSE
