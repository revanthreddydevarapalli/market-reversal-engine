from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.data.providers.base import Bar


def make_bars(rows: list[tuple[float, float, float, float, float]], symbol: str = "TEST") -> list[Bar]:
    """rows: list of (open, high, low, close, volume) tuples, one per bar,
    spaced one hour apart starting at a fixed UTC timestamp."""
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = []
    for i, (o, h, low, c, v) in enumerate(rows):
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=start + timedelta(hours=i),
                open=o,
                high=h,
                low=low,
                close=c,
                volume=v,
            )
        )
    return bars
