"""
Volume profile orchestrator: wires binning + volume allocation + value
area + HVN/LVN detection together into a single `VolumeProfile` for one
symbol/timeframe. Pure function over a list of `Bar` objects -- no I/O,
fully unit-testable with synthetic data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from src.data.providers.base import Bar, Timeframe
from src.volume_profile.binning import compute_bin_edges
from src.volume_profile.nodes import detect_hvn_lvn
from src.volume_profile.value_area import compute_value_area
from src.volume_profile.volume_allocation import allocate_volume


@dataclass
class VolumeProfile:
    symbol: str
    timeframe: Timeframe
    bin_edges: np.ndarray
    volume_by_bin: np.ndarray
    poc: float
    vah: float
    val: float
    hvns: list[dict]
    lvns: list[dict]
    profile_start: datetime
    profile_end: datetime


def build_profile(
    symbol: str,
    timeframe: Timeframe,
    bars: list[Bar],
    bin_count: int,
    value_area_pct: float,
    hvn_lvn_window: int,
    hvn_lvn_min_prominence_pct: float,
) -> VolumeProfile:
    if not bars:
        raise ValueError(f"No bars supplied to build a {timeframe} profile for {symbol}")

    bin_edges = compute_bin_edges(bars, bin_count)
    volume_by_bin = allocate_volume(bars, bin_edges)
    value_area = compute_value_area(volume_by_bin, bin_edges, value_area_pct)
    hvns, lvns = detect_hvn_lvn(volume_by_bin, bin_edges, hvn_lvn_window, hvn_lvn_min_prominence_pct)

    return VolumeProfile(
        symbol=symbol,
        timeframe=timeframe,
        bin_edges=bin_edges,
        volume_by_bin=volume_by_bin,
        poc=value_area["poc"],
        vah=value_area["vah"],
        val=value_area["val"],
        hvns=hvns,
        lvns=lvns,
        profile_start=bars[0].timestamp,
        profile_end=bars[-1].timestamp,
    )
