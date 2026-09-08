"""
Orchestrates: fetch bars for each timeframe -> build volume profiles ->
generate levels (including gap-edge levels, see volume_profile/gaps.py)
-> cluster into confluence zones -> split zones into SUPPORT (below
current price) and RESISTANCE (above current price), ranked by
strength -> (for any zone actually REACHED) run it through the entry
confirmation engine before suggesting a trade.

This is the only module allowed to wire providers + volume_profile +
levels + confirmation + options together, so each of those packages
stays independently testable with plain in-memory data (see CLAUDE.md
principle #4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.config.strategy_params import StrategyParameters
from src.confirmation.engine import ConfirmationResult, run_confirmation_engine
from src.data.providers.base import Bar, OHLCVProvider, OptionsChainProvider, Timeframe
from src.levels.cluster import ConfluenceZone, cluster_levels
from src.levels.generate import levels_from_profile
from src.options.basic_selector import Direction, OptionPick, pick_basic_otm_option
from src.trend.trend import Trend, compute_trend
from src.volume_profile.profile import build_profile

TIMEFRAMES: list[Timeframe] = ["4H", "1D", "1W"]

_LOOKBACK_ATTR: dict[Timeframe, str] = {
    "4H": "lookback_bars_4h",
    "1D": "lookback_bars_1d",
    "1W": "lookback_bars_1w",
}

Status = Literal["WAITING", "NEAR", "REACHED"]
ZoneSide = Literal["SUPPORT", "RESISTANCE"]


@dataclass
class ZoneAnalysis:
    zone: ConfluenceZone
    side: ZoneSide  # SUPPORT = below current price, RESISTANCE = above
    distance_pct: float
    status: Status
    confirmation: ConfirmationResult | None  # only computed when status == REACHED
    option_pick: OptionPick | None
    option_status: str  # "OK" | "NO_LIQUID_CONTRACT_FOUND" | "OPTIONS_PROVIDER_UNAVAILABLE" | "NOT_ATTEMPTED" | "NOT_CONFIRMED"


@dataclass
class SymbolAnalysis:
    symbol: str
    current_price: float
    trend: Trend
    support_zones: list[ZoneAnalysis]     # below price, sorted strongest first
    resistance_zones: list[ZoneAnalysis]  # above price, sorted strongest first


def _zone_status(current_price: float, zone: ConfluenceZone, params: StrategyParameters) -> Status:
    if zone.lower <= current_price <= zone.upper:
        return "REACHED"
    distance_pct = min(
        abs(current_price - zone.lower), abs(current_price - zone.upper)
    ) / current_price
    if distance_pct <= params.reached_tolerance_pct:
        return "REACHED"
    if distance_pct <= params.near_tolerance_pct:
        return "NEAR"
    return "WAITING"


def _pick_option_for_zone(
    side: ZoneSide,
    current_price: float,
    options_provider: OptionsChainProvider | None,
    symbol: str,
    params: StrategyParameters,
    chain: list,
) -> tuple[OptionPick | None, str]:
    """SUPPORT reached -> expecting a bounce up -> LONG_CALL.
    RESISTANCE reached -> expecting a rejection down -> LONG_PUT."""
    if options_provider is None:
        return None, "OPTIONS_PROVIDER_UNAVAILABLE"

    direction: Direction = "LONG_CALL" if side == "SUPPORT" else "LONG_PUT"
    pick = pick_basic_otm_option(
        chain,
        current_price=current_price,
        direction=direction,
        min_dte=params.option_min_dte,
        max_dte=params.option_max_dte,
        min_open_interest=params.option_min_open_interest,
        min_volume=params.option_min_volume,
        target_otm_pct=params.option_target_otm_pct,
    )
    return pick, ("OK" if pick else "NO_LIQUID_CONTRACT_FOUND")


def analyze_symbol(
    symbol: str,
    ohlcv_provider: OHLCVProvider,
    options_provider: OptionsChainProvider | None,
    params: StrategyParameters,
    top_n_per_side: int = 10,
) -> SymbolAnalysis:
    all_levels = []
    bars_by_timeframe: dict[Timeframe, list[Bar]] = {}
    for timeframe in TIMEFRAMES:
        lookback = getattr(params, _LOOKBACK_ATTR[timeframe])
        bars = ohlcv_provider.get_ohlcv(symbol, timeframe, limit=lookback)
        bars_by_timeframe[timeframe] = bars
        profile = build_profile(
            symbol,
            timeframe,
            bars,
            bin_count=params.bin_count,
            value_area_pct=params.value_area_pct,
            hvn_lvn_window=params.hvn_lvn_window,
            hvn_lvn_min_prominence_pct=params.hvn_lvn_min_prominence_pct,
        )
        all_levels.extend(levels_from_profile(profile))

    # Use the freshest (4H) close as "current price" -- not a live quote,
    # but the highest-resolution data this provider gives us.
    current_price = bars_by_timeframe["4H"][-1].close

    trend = compute_trend(
        bars_by_timeframe["1D"], params.trend_lookback_bars, params.trend_flat_threshold_pct
    )

    zones = cluster_levels(all_levels, params.cluster_tolerance_pct)

    # Fetch the option chain once (if a provider is available) and
    # reuse it both for GEX/OI confirmation and for the actual option
    # pick -- avoids hitting the provider twice per reached zone.
    chain = options_provider.get_option_chain(symbol) if options_provider else []

    support_analyses: list[ZoneAnalysis] = []
    resistance_analyses: list[ZoneAnalysis] = []

    for zone in zones:
        side: ZoneSide = "SUPPORT" if current_price >= zone.center else "RESISTANCE"
        distance_pct = abs(zone.center - current_price) / current_price
        status = _zone_status(current_price, zone, params)

        confirmation: ConfirmationResult | None = None
        option_pick, option_status = (None, "NOT_ATTEMPTED")

        if status == "REACHED":
            confirmation = run_confirmation_engine(
                bars_4h=bars_by_timeframe["4H"],
                option_chain=chain,
                current_price=current_price,
                side=side,
                params=params,
            )
            if confirmation.confirmed:
                option_pick, option_status = _pick_option_for_zone(
                    side, current_price, options_provider, symbol, params, chain
                )
            else:
                option_status = "NOT_CONFIRMED"

        support_or_resistance = support_analyses if side == "SUPPORT" else resistance_analyses
        support_or_resistance.append(
            ZoneAnalysis(
                zone=zone,
                side=side,
                distance_pct=distance_pct,
                status=status,
                confirmation=confirmation,
                option_pick=option_pick,
                option_status=option_status,
            )
        )

    support_analyses.sort(key=lambda a: a.zone.base_score, reverse=True)
    resistance_analyses.sort(key=lambda a: a.zone.base_score, reverse=True)

    return SymbolAnalysis(
        symbol=symbol,
        current_price=current_price,
        trend=trend,
        support_zones=support_analyses[:top_n_per_side],
        resistance_zones=resistance_analyses[:top_n_per_side],
    )
