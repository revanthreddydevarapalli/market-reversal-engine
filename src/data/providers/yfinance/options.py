"""
Options-chain adapter backed by yfinance.

IMPORTANT LIMITATION: yfinance's options data is scraped from Yahoo
Finance, is delayed, and carries no uptime/accuracy guarantee. It is
fine for "here's a reasonably liquid contract to look at right now" but
is NOT sufficient for historical backtesting of option trades (no
point-in-time historical chain snapshots). Per CLAUDE.md's
no-fake-history rule, any future backtest that needs historical option
data must mark itself:
    OPTIONS_BACKTEST_STATUS = UNAVAILABLE
rather than substituting live/current chain data for a historical one.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import yfinance as yf

from src.data.providers.base import CallPut, OptionContract


def get_option_chain(symbol: str, max_expirations: int = 6) -> list[OptionContract]:
    ticker = yf.Ticker(symbol)
    expirations = list(ticker.options)[:max_expirations]

    contracts: list[OptionContract] = []
    for exp_str in expirations:
        expiration = datetime.strptime(exp_str, "%Y-%m-%d").replace(tzinfo=UTC)
        chain = ticker.option_chain(exp_str)
        for row in chain.calls.itertuples(index=False):
            contracts.append(_row_to_contract(symbol, expiration, row, "CALL"))
        for row in chain.puts.itertuples(index=False):
            contracts.append(_row_to_contract(symbol, expiration, row, "PUT"))
    return contracts


def _safe_int(value: object) -> int:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: object) -> float | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_to_contract(symbol: str, expiration: datetime, row, call_put: CallPut) -> OptionContract:
    return OptionContract(
        symbol=symbol,
        contract_symbol=row.contractSymbol,
        expiration=expiration,
        strike=float(row.strike),
        call_put=call_put,
        bid=_safe_float(row.bid) or 0.0,
        ask=_safe_float(row.ask) or 0.0,
        last=_safe_float(getattr(row, "lastPrice", None)),
        volume=_safe_int(getattr(row, "volume", None)),
        open_interest=_safe_int(getattr(row, "openInterest", None)),
        implied_volatility=_safe_float(getattr(row, "impliedVolatility", None)),
    )
