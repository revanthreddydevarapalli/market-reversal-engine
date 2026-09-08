"""
Candle-range volume allocation: each candle's volume is split evenly
across every price bin its [low, high] range touches.

This is the documented default method. An alternative (e.g. weighting
allocation toward the candle's close, or using lower-timeframe data to
reconstruct a more granular distribution) is a possible future
methodology version -- not implemented here.
"""

from __future__ import annotations

import numpy as np

from src.data.providers.base import Bar


def allocate_volume(bars: list[Bar], bin_edges: np.ndarray) -> np.ndarray:
    n_bins = len(bin_edges) - 1
    volume_by_bin = np.zeros(n_bins)

    for bar in bars:
        lo_idx = np.searchsorted(bin_edges, bar.low, side="right") - 1
        hi_idx = np.searchsorted(bin_edges, bar.high, side="right") - 1
        lo_idx = max(0, min(lo_idx, n_bins - 1))
        hi_idx = max(0, min(hi_idx, n_bins - 1))

        touched = hi_idx - lo_idx + 1
        if touched <= 0:
            continue

        volume_by_bin[lo_idx : hi_idx + 1] += bar.volume / touched

    return volume_by_bin
