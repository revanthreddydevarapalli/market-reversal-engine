from datetime import UTC, datetime, timedelta

from src.data.providers.base import Bar
from src.trend.trend import compute_trend


def make_closes(closes: list[float]) -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(symbol="TEST", timestamp=start + timedelta(days=i), open=c, high=c, low=c, close=c, volume=100)
        for i, c in enumerate(closes)
    ]


def test_detects_up_trend():
    closes = [100.0] * 5 + [110.0]  # +10% over lookback
    bars = make_closes(closes)
    assert compute_trend(bars, lookback_bars=5, flat_threshold_pct=0.02) == "UP"


def test_detects_down_trend():
    closes = [100.0] * 5 + [90.0]  # -10%
    bars = make_closes(closes)
    assert compute_trend(bars, lookback_bars=5, flat_threshold_pct=0.02) == "DOWN"


def test_small_move_is_flat():
    closes = [100.0] * 5 + [100.5]  # +0.5%, under 2% threshold
    bars = make_closes(closes)
    assert compute_trend(bars, lookback_bars=5, flat_threshold_pct=0.02) == "FLAT"


def test_insufficient_bars_is_flat():
    bars = make_closes([100.0])
    assert compute_trend(bars, lookback_bars=20, flat_threshold_pct=0.02) == "FLAT"


def test_lookback_longer_than_history_uses_earliest_available():
    closes = [100.0, 105.0, 110.0]  # only 3 bars, lookback asks for 20
    bars = make_closes(closes)
    # Should compare against the earliest bar (100.0) rather than error.
    assert compute_trend(bars, lookback_bars=20, flat_threshold_pct=0.02) == "UP"
