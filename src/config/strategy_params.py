"""
Strategy/methodology parameters for the V1-lite scope: best confluence
levels + a basic OTM-liquid option suggestion. Per CLAUDE.md principle
#3, these live in one place (not scattered as magic numbers) and are all
overridable. This is deliberately a plain, versioned Pydantic model
rather than environment variables, since these are trading-methodology
choices, not infrastructure config -- and every analysis result should
be able to report which parameter set produced it.

None of these defaults are claims that they are optimal. They are
documented, reasonable starting points (labeled ASSUMPTION where a real
methodological choice was made) meant to be tuned/backtested later.
"""

from pydantic import BaseModel, Field


class StrategyParameters(BaseModel):
    version: str = "0.1.0-lite"

    # --- Volume profile ---
    # ASSUMPTION: fixed bin count chosen as the default binning method for
    # simplicity/determinism. Tick-size and adaptive binning are deferred.
    # 150 (rather than a rounder 100) was chosen after live comparison
    # against a manually-drawn TradingView volume profile on NVDA showed
    # 100 bins was too coarse and blended together real, visually-
    # confirmable levels (see CLAUDE.md changelog note below).
    bin_count: int = Field(default=150, gt=0)
    value_area_pct: float = Field(default=0.70, gt=0, lt=1)

    # ASSUMPTION: how many historical bars to pull per timeframe before
    # building a profile. This matters more than it looks: a fixed-bin
    # profile spans [min(low), max(high)] of whatever bars it's given,
    # so too long a lookback on a stock that has moved a lot (e.g. 500
    # weekly bars = ~9.6 years) mixes wildly different price regimes
    # into one profile. Old, thinly-touched bins at the edge of that
    # huge range can then get misdetected as HVN/LVN simply because
    # they're an isolated non-zero bin next to a sea of zero-volume
    # bins -- not because they're a real, currently-relevant level.
    # These defaults keep each timeframe's lookback within a more
    # coherent price regime; tune per-symbol if a name has moved a lot.
    lookback_bars_4h: int = Field(default=500, gt=0)   # ~83 trading days
    lookback_bars_1d: int = Field(default=252, gt=0)   # ~1 trading year
    lookback_bars_1w: int = Field(default=104, gt=0)   # ~2 years

    # ASSUMPTION: HVN/LVN are local extrema within +/- `hvn_lvn_window`
    # bins, accepted only if they deviate from their local neighborhood
    # mean by at least `hvn_lvn_min_prominence_pct` of that mean. Lowered
    # from an initial 0.15 to 0.05 after live comparison against a
    # manually-drawn TradingView volume profile on NVDA showed 0.15 was
    # filtering out real, visually-confirmable nodes (e.g. a level near
    # $215 that only appeared once the threshold was loosened). This is
    # still an unvalidated heuristic threshold, not backtested -- revisit
    # once real backtesting exists.
    hvn_lvn_window: int = Field(default=3, gt=0)
    hvn_lvn_min_prominence_pct: float = Field(default=0.05, ge=0)

    # --- Level clustering ---
    # ASSUMPTION: flat percentage-of-price tolerance (not volatility-aware
    # yet). Two levels join the same confluence zone if within this % of
    # each other.
    cluster_tolerance_pct: float = Field(default=0.0025, gt=0)

    # --- Zone status thresholds (display only, not a trading signal) ---
    reached_tolerance_pct: float = Field(default=0.001, gt=0)
    near_tolerance_pct: float = Field(default=0.01, gt=0)

    # --- Basic option selection (v1-lite; see src/options/basic_selector.py) ---
    option_min_dte: int = Field(default=14, ge=0)
    option_max_dte: int = Field(default=45, ge=0)
    option_min_open_interest: int = Field(default=100, ge=0)
    option_min_volume: int = Field(default=10, ge=0)
    # ASSUMPTION: "basic OTM" targets ~3% out of the money by default,
    # searching for the closest liquid contract to that distance.
    option_target_otm_pct: float = Field(default=0.03, gt=0)

    # --- Trend-based zone prioritization (see src/trend/trend.py) ---
    # ASSUMPTION: crude momentum heuristic, not a validated signal.
    trend_lookback_bars: int = Field(default=20, gt=0)  # ~1 trading month on 1D bars
    trend_flat_threshold_pct: float = Field(default=0.02, ge=0)

    # --- Entry confirmation engine (see src/confirmation/) ---
    # ASSUMPTION: all of the below are standard ICT/price-action
    # definitions and reasonable defaults, not backtested constants.
    # A REACHED zone only gets an option suggestion if at least
    # `confirm_min_confirmations` of the 4 checks pass.
    confirm_swing_lookback: int = Field(default=3, gt=0)
    confirm_sweep_reclaim_window: int = Field(default=3, gt=0)
    confirm_fvg_lookback_bars: int = Field(default=20, gt=0)
    confirm_ob_lookback_bars: int = Field(default=20, gt=0)
    confirm_price_proximity_pct: float = Field(default=0.01, gt=0)
    confirm_oi_proximity_pct: float = Field(default=0.02, gt=0)
    # ASSUMPTION: 500 combined OI within confirm_oi_proximity_pct is an
    # arbitrary "meaningful concentration" bar -- tune per symbol
    # (mega-caps like NVDA/AAPL will clear this easily; smaller/less
    # liquid names may need a lower threshold).
    confirm_min_oi_wall: int = Field(default=500, ge=0)
    # ASSUMPTION: require at least half of the 4 checks (2 of 4) to
    # agree by default. Raise for a stricter bot, lower to see more
    # (unconfirmed) candidates for research purposes.
    confirm_min_confirmations: int = Field(default=2, ge=0, le=4)


DEFAULT_STRATEGY_PARAMETERS = StrategyParameters()
