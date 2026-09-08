"""
POC / VAH / VAL calculation.

POC = the bin with the highest allocated volume.

Value area = the smallest contiguous band of bins, expanding outward
from the POC, whose cumulative volume reaches `value_area_pct` of total
volume. At each expansion step, whichever adjacent bin (immediately
above or below the current band) has more volume is added next. Default
`value_area_pct` is 70% (documented, configurable) -- not assumed to be
optimal; a target for future backtesting against alternatives.
"""

from __future__ import annotations

import numpy as np


def compute_value_area(
    volume_by_bin: np.ndarray, bin_edges: np.ndarray, value_area_pct: float = 0.70
) -> dict:
    total = volume_by_bin.sum()
    if total <= 0:
        raise ValueError("Cannot compute value area with zero total volume")

    poc_idx = int(np.argmax(volume_by_bin))
    lo_idx, hi_idx = poc_idx, poc_idx
    covered = volume_by_bin[poc_idx]
    target = total * value_area_pct

    while covered < target and (lo_idx > 0 or hi_idx < len(volume_by_bin) - 1):
        vol_below = volume_by_bin[lo_idx - 1] if lo_idx > 0 else -1.0
        vol_above = volume_by_bin[hi_idx + 1] if hi_idx < len(volume_by_bin) - 1 else -1.0

        if vol_above >= vol_below:
            hi_idx += 1
            covered += volume_by_bin[hi_idx]
        else:
            lo_idx -= 1
            covered += volume_by_bin[lo_idx]

    poc_price = float((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2)
    val_price = float(bin_edges[lo_idx])
    vah_price = float(bin_edges[hi_idx + 1])

    return {
        "poc": poc_price,
        "val": val_price,
        "vah": vah_price,
        "poc_idx": poc_idx,
        "lo_idx": lo_idx,
        "hi_idx": hi_idx,
    }
