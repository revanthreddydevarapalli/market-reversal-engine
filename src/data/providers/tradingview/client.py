"""
OHLCV adapter for https://github.com/MrChartist/tradingview-scraper.

That project is itself a small FastAPI service (a wrapper around
TradingView's websocket feed). The cleanest integration is to run it as
its own process/container and call its HTTP API -- this engine never
imports its internals, so it stays swappable for another OHLCV source
(see `src/data/providers/base.py`).

Run it separately, e.g.:
    git clone https://github.com/MrChartist/tradingview-scraper.git
    cd tradingview-scraper && pip install -r requirements.txt -r api/requirements.txt
    uvicorn api.main:app --port 8100   # NOTE: pick a port other than
                                        # this engine's own (8000)

Then point this engine at it via TRADINGVIEW_SCRAPER_BASE_URL
(default: http://localhost:8100).

Endpoint used (per that repo's README):
    GET /api/ohlcv/{exchange}/{ticker}?timeframe=...&candles=...
Response shape:
    [{"index": 0, "timestamp": 1712534400, "open": ..., "high": ...,
      "low": ..., "close": ..., "volume": ...}, ...]

ASSUMPTIONS (verified against a live instance on 2026-09-07 — confirmed
correct, do not change without re-verifying):
  - `timestamp` is epoch seconds, UTC.
  - The `timeframe` query param takes lowercase strings: "4h", "1d",
    "1w". Uppercase ("1D", "1W") or numeric-minute strings ("240") are
    silently NOT recognized by this service and fall back to raw
    1-minute bars with no error -- this was caught by comparing gaps
    between consecutive returned timestamps.
  - Futures/index symbols (ES, NQ, YM, RTY) need a specific exchange
    prefix (e.g. CME_MINI); equities default to NASDAQ. Both are
    overridable per-symbol via `exchange_map`. NOT yet verified live
    for futures symbols -- verify before relying on ES/NQ/YM/RTY data.
  - Response shape is `{"status": "success", "data": [...], "total": N}`,
    NOT a bare list as the repo's top-level README example suggested.
    The `data` key is unwrapped in `get_ohlcv` below.
"""

from __future__ import annotations

from datetime import UTC, datetime

import requests

from src.data.providers.base import Bar, Timeframe

DEFAULT_EXCHANGE = "NASDAQ"
DEFAULT_EXCHANGE_MAP: dict[str, str] = {
    "ES": "CME_MINI",
    "NQ": "CME_MINI",
    "YM": "CBOT_MINI",
    "RTY": "CME_MINI",
}
# Verified live 2026-09-07: this service expects lowercase strings and
# silently ignores unrecognized ones (falling back to raw 1-minute data
# with no error), so exact casing matters.
_TIMEFRAME_MAP: dict[Timeframe, str] = {
    "4H": "4h",
    "1D": "1d",
    "1W": "1w",
}


class TradingViewScraperProvider:
    """OHLCVProvider backed by a running tradingview-scraper instance."""

    def __init__(
        self,
        base_url: str,
        exchange_map: dict[str, str] | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.exchange_map = {**DEFAULT_EXCHANGE_MAP, **(exchange_map or {})}
        self.timeout = timeout

    def _exchange_for(self, symbol: str) -> str:
        return self.exchange_map.get(symbol.upper(), DEFAULT_EXCHANGE)

    def get_ohlcv(self, symbol: str, timeframe: Timeframe, limit: int = 500) -> list[Bar]:
        if timeframe not in _TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        exchange = self._exchange_for(symbol)
        url = f"{self.base_url}/api/ohlcv/{exchange}/{symbol}"
        response = requests.get(
            url,
            params={"timeframe": _TIMEFRAME_MAP[timeframe], "candles": limit},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data", []) if isinstance(payload, dict) else payload

        bars = [self._row_to_bar(symbol, row) for row in rows]
        bars.sort(key=lambda b: b.timestamp)
        return bars

    @staticmethod
    def _row_to_bar(symbol: str, row: dict) -> Bar:
        return Bar(
            symbol=symbol,
            timestamp=datetime.fromtimestamp(row["timestamp"], tz=UTC),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )
