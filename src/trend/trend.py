"""
Simple price-momentum trend classifier.

NOT the ES/NQ/YM/RTY market-regime engine from the original master spec
(that's a separate, not-yet-built concept comparing broader index
direction). This is much narrower: "has this symbol's own price been
net up, down, or flat over the last N bars," used only to decide which
side of price (support below vs resistance above) is more likely to be
the next relevant zone to watch.

ASSUMPTION: momentum is measured as simple % change from N bars ago to
the most recent close on the daily timeframe -- not a moving-average
crossover, not multi-timeframe confirmation, not volume-weighted. This
is a deliberately crude heuristic for prioritizing which zone to
surface first, not a validated directional signal. It will be wrong
in choppy/range-bound conditions, which is exactly why FLAT exists as
an explicit third state rather than forcing every case into UP/DOWN.
"""

from __future__ import annotations

from typing import Literal

from src.data.providers.base import Bar

Trend = Literal["UP", "DOWN", "FLAT"]


def compute_trend(bars: list[Bar], lookback_bars: int, flat_threshold_pct: float) -> Trend:
    if len(bars) < 2:
        return "FLAT"

    lookback = min(lookback_bars, len(bars) - 1)
    recent_close = bars[-1].close
    past_close = bars[-1 - lookback].close

    if past_close == 0:
        return "FLAT"

    pct_change = (recent_close - past_close) / past_close

    if abs(pct_change) < flat_threshold_pct:
        return "FLAT"
    return "UP" if pct_change > 0 else "DOWN"
