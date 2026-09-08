"""
Provider-agnostic data contracts. Nothing in volume_profile/, levels/,
options/, or services/ should import a specific provider (TradingView
scraper, yfinance, etc.) directly -- they depend only on `Bar`,
`OptionContract`, and the two Protocols below, so a provider can be
swapped without touching analytics code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

Timeframe = Literal["4H", "1D", "1W"]
CallPut = Literal["CALL", "PUT"]


@dataclass(frozen=True)
class Bar:
    symbol: str
    timestamp: datetime  # must be timezone-aware, normalized to UTC
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class OptionContract:
    symbol: str
    contract_symbol: str
    expiration: datetime  # timezone-aware, UTC
    strike: float
    call_put: CallPut
    bid: float
    ask: float
    last: float | None
    volume: int
    open_interest: int
    implied_volatility: float | None


class OHLCVProvider(Protocol):
    def get_ohlcv(self, symbol: str, timeframe: Timeframe, limit: int = 500) -> list[Bar]: ...


class OptionsChainProvider(Protocol):
    def get_option_chain(self, symbol: str) -> list[OptionContract]: ...
