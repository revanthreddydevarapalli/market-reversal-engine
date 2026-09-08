"""
ICT-style price-action concepts, computed deterministically from OHLCV.

- LIQUIDITY SWEEP: price briefly trades beyond a recent swing high/low
  (triggering stops resting there) and then closes back on the other
  side within the same or next few bars -- a classic "stop hunt" that
  often precedes a reversal, since it suggests the move beyond the
  level was liquidity-grabbing rather than genuine breakout continuation.
- FAIR VALUE GAP (FVG): a 3-bar pattern where bar 1's high is below
  bar 3's low (bullish FVG) or bar 1's low is above bar 3's high
  (bearish FVG) -- i.e. bar 2 creates a price range that wasn't traded
  by bars 1 or 3 on one side, leaving an "imbalance" the market often
  later revisits.
- ORDER BLOCK: the last down-close candle before a strong up-move (a
  bullish order block) or the last up-close candle before a strong
  down-move (a bearish order block) -- the idea being that's where
  larger participants likely built their position before the move.

ASSUMPTION: all thresholds below (sweep confirmation window, "strong
move" multiplier for order blocks) are configurable heuristics, not
backtested constants. These are standard ICT definitions as commonly
described, not a proprietary or validated methodology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.confirmation.market_structure import find_swing_points
from src.data.providers.base import Bar

FVGType = Literal["BULLISH", "BEARISH"]
OrderBlockType = Literal["BULLISH", "BEARISH"]


@dataclass(frozen=True)
class LiquiditySweep:
    swept_price: float
    swept_kind: Literal["HIGH", "LOW"]
    reclaim_index: int


@dataclass(frozen=True)
class FairValueGap:
    gap_low: float
    gap_high: float
    kind: FVGType
    index: int


@dataclass(frozen=True)
class OrderBlock:
    low: float
    high: float
    kind: OrderBlockType
    index: int


def detect_recent_liquidity_sweep(
    bars: list[Bar], swing_lookback: int = 3, reclaim_window: int = 3
) -> LiquiditySweep | None:
    """Checks whether, within the last `reclaim_window` bars, price
    poked beyond a prior swing high/low and then closed back inside --
    a stop-hunt pattern. Returns the most recent such sweep, if any."""
    swings = find_swing_points(bars, swing_lookback)
    if not swings or len(bars) < reclaim_window + 1:
        return None

    highs = [s for s in swings if s.kind == "HIGH"]
    lows = [s for s in swings if s.kind == "LOW"]

    recent_bars = bars[-reclaim_window:]
    last_close = bars[-1].close

    if highs:
        prior_high = highs[-1].price
        poked_above = any(b.high > prior_high for b in recent_bars)
        if poked_above and last_close < prior_high:
            return LiquiditySweep(swept_price=prior_high, swept_kind="HIGH", reclaim_index=len(bars) - 1)

    if lows:
        prior_low = lows[-1].price
        poked_below = any(b.low < prior_low for b in recent_bars)
        if poked_below and last_close > prior_low:
            return LiquiditySweep(swept_price=prior_low, swept_kind="LOW", reclaim_index=len(bars) - 1)

    return None


def detect_fair_value_gaps(bars: list[Bar], lookback_bars: int = 20) -> list[FairValueGap]:
    gaps: list[FairValueGap] = []
    start = max(2, len(bars) - lookback_bars)
    for i in range(start, len(bars)):
        b1, b3 = bars[i - 2], bars[i]
        if b1.high < b3.low:
            gaps.append(FairValueGap(gap_low=b1.high, gap_high=b3.low, kind="BULLISH", index=i))
        elif b1.low > b3.high:
            gaps.append(FairValueGap(gap_low=b3.high, gap_high=b1.low, kind="BEARISH", index=i))
    return gaps


def detect_order_blocks(
    bars: list[Bar], lookback_bars: int = 20, strong_move_atr_multiplier: float = 1.5
) -> list[OrderBlock]:
    if len(bars) < 10:
        return []

    # Simple ATR proxy: average true range over the lookback window,
    # used to decide what counts as a "strong" move worth marking an
    # order block for (avoids flagging every minor up/down candle).
    start = max(1, len(bars) - lookback_bars)
    ranges = [bars[i].high - bars[i].low for i in range(start, len(bars))]
    avg_range = sum(ranges) / len(ranges) if ranges else 0.0
    if avg_range <= 0:
        return []

    blocks: list[OrderBlock] = []
    for i in range(start, len(bars) - 1):
        move = bars[i + 1].close - bars[i].close
        is_strong = abs(move) >= avg_range * strong_move_atr_multiplier

        if not is_strong:
            continue

        if move > 0 and bars[i].close < bars[i].open:
            # Last down-candle before a strong up-move -> bullish OB.
            blocks.append(OrderBlock(low=bars[i].low, high=bars[i].high, kind="BULLISH", index=i))
        elif move < 0 and bars[i].close > bars[i].open:
            # Last up-candle before a strong down-move -> bearish OB.
            blocks.append(OrderBlock(low=bars[i].low, high=bars[i].high, kind="BEARISH", index=i))

    return blocks
