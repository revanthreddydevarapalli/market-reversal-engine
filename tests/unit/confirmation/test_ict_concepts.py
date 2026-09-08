from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.confirmation.ict_concepts import detect_fair_value_gaps, detect_order_blocks, detect_recent_liquidity_sweep
from src.data.providers.base import Bar


def make_bars(rows: list[tuple[float, float, float, float]]) -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(symbol="TEST", timestamp=start + timedelta(hours=i), open=o, high=h, low=l, close=c, volume=1000)
        for i, (o, h, l, c) in enumerate(rows)
    ]


def test_detects_bullish_fair_value_gap():
    # bar0 high=105, bar1 anything, bar2 low=110 -> gap between 105 and 110.
    rows = [(100, 105, 99, 104), (104, 108, 103, 107), (107, 115, 110, 114)]
    bars = make_bars(rows)
    gaps = detect_fair_value_gaps(bars, lookback_bars=10)
    assert len(gaps) == 1
    assert gaps[0].kind == "BULLISH"
    assert gaps[0].gap_low == 105
    assert gaps[0].gap_high == 110


def test_detects_bearish_fair_value_gap():
    rows = [(115, 116, 110, 111), (111, 112, 106, 107), (107, 104, 100, 102)]
    bars = make_bars(rows)
    gaps = detect_fair_value_gaps(bars, lookback_bars=10)
    assert len(gaps) == 1
    assert gaps[0].kind == "BEARISH"


def test_no_gap_when_ranges_overlap():
    rows = [(100, 105, 99, 104), (104, 108, 103, 107), (107, 109, 102, 106)]
    bars = make_bars(rows)
    assert detect_fair_value_gaps(bars, lookback_bars=10) == []


def test_liquidity_sweep_detects_stop_hunt_and_reclaim():
    # Downtrend forms a swing low at 95, then price pokes below (93) and
    # closes back above 95 within the reclaim window -> LOW sweep.
    rows = [
        (110, 111, 108, 109),
        (109, 110, 100, 101),
        (101, 102, 95, 96),   # swing low candidate ~95
        (96, 100, 96, 99),
        (99, 103, 99, 102),
        (102, 103, 93, 96),   # pokes below 95...
        (96, 99, 95, 98),     # ...and closes back above 95
    ]
    bars = make_bars(rows)
    sweep = detect_recent_liquidity_sweep(bars, swing_lookback=2, reclaim_window=3)
    assert sweep is not None
    assert sweep.swept_kind == "LOW"


def test_no_sweep_when_nothing_reclaimed():
    rows = [(100, 101, 99, 100)] * 10
    bars = make_bars(rows)
    assert detect_recent_liquidity_sweep(bars, swing_lookback=2, reclaim_window=3) is None


def test_detects_bullish_order_block():
    # A down-close candle immediately followed by a strong up-move.
    rows = [(100, 101, 98, 99)] * 8  # quiet baseline for ATR (need >=10 bars total)
    rows.append((100, 101, 97, 98))   # down-close candle (order block candidate)
    rows.append((98, 115, 98, 114))   # strong up move next bar
    bars = make_bars(rows)
    blocks = detect_order_blocks(bars, lookback_bars=10, strong_move_atr_multiplier=1.5)
    bullish = [b for b in blocks if b.kind == "BULLISH"]
    assert len(bullish) >= 1
