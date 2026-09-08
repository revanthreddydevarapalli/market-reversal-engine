from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.confirmation.market_structure import detect_structure_event, find_swing_points
from src.data.providers.base import Bar


def make_bars(closes: list[tuple[float, float, float, float]]) -> list[Bar]:
    """closes: list of (open, high, low, close) tuples."""
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(symbol="TEST", timestamp=start + timedelta(hours=i), open=o, high=h, low=l, close=c, volume=1000)
        for i, (o, h, l, c) in enumerate(closes)
    ]


def test_finds_a_clear_swing_high():
    # Rises to a peak at index 5, then falls -- index 5 should be a swing high.
    rows = [(100, 101, 99, 100)] * 2 + [(100, 102, 100, 101), (101, 104, 101, 103), (103, 106, 103, 105),
                                          (105, 110, 105, 108),  # peak
                                          (108, 108, 104, 105), (105, 105, 100, 101)] + [(100, 101, 99, 100)] * 2
    bars = make_bars(rows)
    swings = find_swing_points(bars, swing_lookback=2)
    high_indices = [s.index for s in swings if s.kind == "HIGH"]
    assert 5 in high_indices


def test_choch_up_detected_after_downtrend_reversal():
    # Explicit downtrend: lower highs, lower lows (swing high 109 -> 103,
    # swing low 103 -> 95 -> 85), then a sharp break closing above the
    # most recent swing high (103) -- against the downtrend -> CHoCH_UP.
    rows = [
        (110, 111, 108, 109),
        (109, 110, 105, 106),
        (106, 107, 103, 104),
        (104, 108, 104, 107),
        (107, 109, 106, 108),
        (108, 108, 100, 101),
        (101, 102, 95, 96),
        (96, 100, 96, 99),
        (99, 103, 99, 102),
        (102, 102, 90, 91),
        (91, 92, 85, 86),
        (86, 95, 86, 94),
        (94, 115, 94, 114),  # strong break, closes above recent swing high
    ]
    bars = make_bars(rows)
    assert detect_structure_event(bars, swing_lookback=2) == "CHOCH_UP"


def test_insufficient_data_returns_none():
    bars = make_bars([(100, 101, 99, 100)] * 3)
    assert detect_structure_event(bars, swing_lookback=3) == "NONE"
