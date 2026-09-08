"""
Turns a VolumeProfile into a flat list of individual `Level` objects
(POC/VAH/VAL/HVN/LVN), each carrying enough metadata to later be
clustered and scored.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.volume_profile.profile import VolumeProfile

LevelType = Literal["POC", "VAH", "VAL", "HVN", "LVN"]


@dataclass(frozen=True)
class Level:
    symbol: str
    timeframe: str
    level_type: LevelType
    price: float
    relative_volume: float  # volume at level relative to mean bin volume


def levels_from_profile(profile: VolumeProfile) -> list[Level]:
    mean_vol = profile.volume_by_bin.mean()

    levels = [
        Level(profile.symbol, profile.timeframe, "POC", profile.poc, 1.0),
        Level(profile.symbol, profile.timeframe, "VAH", profile.vah, 1.0),
        Level(profile.symbol, profile.timeframe, "VAL", profile.val, 1.0),
    ]

    for hvn in profile.hvns:
        rel_vol = (hvn["volume"] / mean_vol) if mean_vol else 0.0
        levels.append(Level(profile.symbol, profile.timeframe, "HVN", hvn["price"], rel_vol))

    for lvn in profile.lvns:
        rel_vol = (lvn["volume"] / mean_vol) if mean_vol else 0.0
        levels.append(Level(profile.symbol, profile.timeframe, "LVN", lvn["price"], rel_vol))

    return levels
