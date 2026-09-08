"""
Level clustering: group levels from different timeframes/types into
confluence zones. Uses a simple deterministic rule -- sort levels by
price, then walk through them left to right, starting a new cluster
whenever the gap to the previous level exceeds `tolerance_pct` of that
level's price.

ASSUMPTION: tolerance is a flat percentage of price, not volatility-
aware -- a documented simplification, not a claim it's optimal.

Also computes a BASE_SCORE per zone: a deterministic, non-statistically-
validated research heuristic (see CLAUDE.md #6/#8) meant only to rank
zones relative to each other right now, not to claim a reversal
probability.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.levels.generate import Level

# ASSUMPTION: weekly/daily levels are treated as more significant than
# 4H levels for the base score. This is an untested prior the backtester
# should eventually validate or refute.
TIMEFRAME_WEIGHT: dict[str, float] = {"1W": 3.0, "1D": 2.0, "4H": 1.0}
LEVEL_TYPE_WEIGHT: dict[str, float] = {
    "POC": 1.5,
    "VAH": 1.0,
    "VAL": 1.0,
    "HVN": 1.0,
    "LVN": 0.5,
}


@dataclass
class ConfluenceZone:
    lower: float
    upper: float
    center: float
    levels: list[Level]

    @property
    def timeframes_present(self) -> set[str]:
        return {lv.timeframe for lv in self.levels}

    @property
    def level_types_present(self) -> set[str]:
        return {lv.level_type for lv in self.levels}

    @property
    def base_score(self) -> float:
        """Deterministic, unvalidated research score -- NOT a probability."""
        score = sum(
            TIMEFRAME_WEIGHT.get(lv.timeframe, 1.0) * LEVEL_TYPE_WEIGHT.get(lv.level_type, 1.0)
            for lv in self.levels
        )
        confluence_bonus = 1.0 + 0.25 * (len(self.timeframes_present) - 1)
        return round(score * confluence_bonus, 3)

    @property
    def strength_stars(self) -> int:
        """Maps base_score onto a 1-5 star DISPLAY bucket. These
        thresholds are arbitrary display buckets, not a statistically
        validated scale -- do not present as a win-rate proxy."""
        score = self.base_score
        if score >= 10:
            return 5
        if score >= 7:
            return 4
        if score >= 4.5:
            return 3
        if score >= 2:
            return 2
        return 1


def cluster_levels(levels: list[Level], tolerance_pct: float) -> list[ConfluenceZone]:
    if not levels:
        return []

    sorted_levels = sorted(levels, key=lambda lv: lv.price)
    clusters: list[list[Level]] = [[sorted_levels[0]]]

    for lv in sorted_levels[1:]:
        cluster_ref_price = clusters[-1][-1].price
        if abs(lv.price - cluster_ref_price) <= tolerance_pct * cluster_ref_price:
            clusters[-1].append(lv)
        else:
            clusters.append([lv])

    zones = []
    for cluster in clusters:
        prices = [lv.price for lv in cluster]
        lower, upper = min(prices), max(prices)
        center = sum(prices) / len(prices)
        zones.append(ConfluenceZone(lower=lower, upper=upper, center=center, levels=cluster))

    return zones
