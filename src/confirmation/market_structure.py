"""
Market structure detection: swing highs/lows, Break of Structure (BOS),
and Change of Character (CHoCH).

Standard price-action definitions used here:

- A SWING HIGH is a bar whose high is higher than the highs of
  `swing_lookback` bars on both sides of it. A SWING LOW is the mirror
  (lowest low in its neighborhood).
- BOS (Break of Structure): price closes beyond the most recent swing
  point IN THE DIRECTION OF THE EXISTING TREND -- confirms the trend is
  continuing (e.g. in an uptrend, closing above the last swing high).
- CHoCH (Change of Character): price closes beyond the most recent
  swing point AGAINST the prior trend direction -- the first sign the
  trend may be reversing (e.g. in an uptrend, closing below the most
  recent swing low).

ASSUMPTION: "trend direction" for BOS/CHoCH purposes is inferred from
the sequence of recent swing points (higher highs + higher lows = up;
lower highs + lower lows = down) rather than a separate indicator. This
is the standard ICT/price-action definition, but it's still a
deterministic heuristic on a limited lookback window, not a proven
signal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.data.providers.base import Bar

SwingType = Literal["HIGH", "LOW"]
StructureEvent = Literal["BOS_UP", "BOS_DOWN", "CHOCH_UP", "CHOCH_DOWN", "NONE"]


@dataclass(frozen=True)
class SwingPoint:
    index: int
    price: float
    kind: SwingType


def find_swing_points(bars: list[Bar], swing_lookback: int = 3) -> list[SwingPoint]:
    swings: list[SwingPoint] = []
    n = len(bars)
    for i in range(swing_lookback, n - swing_lookback):
        window_highs = [bars[j].high for j in range(i - swing_lookback, i + swing_lookback + 1)]
        window_lows = [bars[j].low for j in range(i - swing_lookback, i + swing_lookback + 1)]

        if bars[i].high == max(window_highs) and window_highs.count(bars[i].high) == 1:
            swings.append(SwingPoint(index=i, price=bars[i].high, kind="HIGH"))
        if bars[i].low == min(window_lows) and window_lows.count(bars[i].low) == 1:
            swings.append(SwingPoint(index=i, price=bars[i].low, kind="LOW"))

    swings.sort(key=lambda s: s.index)
    return swings


def detect_structure_event(bars: list[Bar], swing_lookback: int = 3) -> StructureEvent:
    """Looks at the most recent swing high and swing low, and whether
    the latest close has broken beyond either -- and whether that break
    agrees with (BOS) or contradicts (CHoCH) the recent swing sequence."""
    swings = find_swing_points(bars, swing_lookback)
    if len(swings) < 2:
        return "NONE"

    highs = [s for s in swings if s.kind == "HIGH"]
    lows = [s for s in swings if s.kind == "LOW"]
    if not highs or not lows:
        return "NONE"

    last_high = highs[-1]
    last_low = lows[-1]
    latest_close = bars[-1].close

    # Infer recent trend direction from the last two swings of each kind.
    trend_up = len(highs) >= 2 and len(lows) >= 2 and highs[-1].price > highs[-2].price and lows[-1].price > lows[-2].price
    trend_down = len(highs) >= 2 and len(lows) >= 2 and highs[-1].price < highs[-2].price and lows[-1].price < lows[-2].price

    broke_above_high = latest_close > last_high.price
    broke_below_low = latest_close < last_low.price

    if broke_above_high:
        return "BOS_UP" if trend_up or not trend_down else "CHOCH_UP"
    if broke_below_low:
        return "BOS_DOWN" if trend_down or not trend_up else "CHOCH_DOWN"
    return "NONE"
