"""
Price binning strategy.

Default method (v1-lite): FIXED_BIN_COUNT -- split the [low, high] range
of the input bars into `bin_count` equal-width bins. Deterministic: the
same bars + same bin_count always produce the same bin edges.

ASSUMPTION: fixed-bin-count was chosen as the default for simplicity and
determinism. Fixed-tick-size and adaptive/volatility-aware binning
(both mentioned in the original spec) are not implemented in this lite
version but the function signature is isolated so a new method can be
swapped in without touching callers.
"""

from __future__ import annotations

import numpy as np

from src.data.providers.base import Bar


def compute_bin_edges(bars: list[Bar], bin_count: int) -> np.ndarray:
    if not bars:
        raise ValueError("Cannot compute bins for an empty bar list")

    lo = min(b.low for b in bars)
    hi = max(b.high for b in bars)
    if hi <= lo:
        # Degenerate case (e.g. a single flat bar) -- widen slightly so
        # binning still produces a valid, non-zero-width range.
        hi = lo + 1e-6

    return np.linspace(lo, hi, bin_count + 1)
