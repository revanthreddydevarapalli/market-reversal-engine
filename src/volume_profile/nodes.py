"""
HVN/LVN detection: local maxima/minima in the volume distribution,
relative to a rolling neighborhood, accepted only if they clear a
minimum-prominence threshold measured as a fraction of that
neighborhood's mean volume. Deterministic and reproducible from the
same (volume_by_bin, window, min_prominence_pct) inputs -- no manual/
visual interpretation involved.
"""

from __future__ import annotations

import numpy as np


def detect_hvn_lvn(
    volume_by_bin: np.ndarray,
    bin_edges: np.ndarray,
    window: int = 3,
    min_prominence_pct: float = 0.15,
) -> tuple[list[dict], list[dict]]:
    n = len(volume_by_bin)
    hvns: list[dict] = []
    lvns: list[dict] = []

    for i in range(n):
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        neighborhood = volume_by_bin[lo:hi]
        neighborhood_mean = neighborhood.mean()
        threshold = neighborhood_mean * min_prominence_pct
        price = float((bin_edges[i] + bin_edges[i + 1]) / 2)

        if volume_by_bin[i] == neighborhood.max() and (volume_by_bin[i] - neighborhood_mean) >= threshold:
            hvns.append({"price": price, "volume": float(volume_by_bin[i]), "bin_index": i})

        if volume_by_bin[i] == neighborhood.min() and (neighborhood_mean - volume_by_bin[i]) >= threshold:
            lvns.append({"price": price, "volume": float(volume_by_bin[i]), "bin_index": i})

    return hvns, lvns
