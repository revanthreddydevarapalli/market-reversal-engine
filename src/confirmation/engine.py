"""
Multi-factor entry confirmation engine.

A level being REACHED is necessary but not sufficient for a trade
signal -- that was the whole point of this addition. This engine checks
several independent, deterministic signals and only marks a candidate
CONFIRMED if at least `confirm_min_confirmations` of them agree. This
is the "check the signs, not just the touch" layer.

Checks:
1. market_structure -- was there a CHoCH (Change of Character) in our
   favor recently? (see market_structure.py)
2. liquidity_sweep -- did price sweep a recent swing high/low and
   reclaim it? (stop-hunt-then-reverse pattern)
3. fvg_or_order_block -- is there a Fair Value Gap or Order Block near
   current price, in the direction we'd be trading?
4. options_positioning -- is there a meaningful open-interest
   concentration near this price? (see options_positioning.py --
   an approximation, not real dealer data)

This is a deterministic checklist, explicitly NOT backtested or
statistically validated. A CONFIRMED result means "several independent
heuristics agree," not "this will work." See CLAUDE.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.confirmation.ict_concepts import detect_fair_value_gaps, detect_order_blocks, detect_recent_liquidity_sweep
from src.confirmation.market_structure import detect_structure_event
from src.confirmation.options_positioning import open_interest_wall_near
from src.config.strategy_params import StrategyParameters
from src.data.providers.base import Bar, OptionContract

Side = Literal["SUPPORT", "RESISTANCE"]


@dataclass
class ConfirmationCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class ConfirmationResult:
    confirmed: bool
    checks: list[ConfirmationCheck] = field(default_factory=list)
    confirmations_passed: int = 0
    confirmations_required: int = 0


def run_confirmation_engine(
    bars_4h: list[Bar],
    option_chain: list[OptionContract],
    current_price: float,
    side: Side,
    params: StrategyParameters,
) -> ConfirmationResult:
    checks: list[ConfirmationCheck] = []

    # 1. Market structure: CHoCH in our favor.
    # SUPPORT reached (expecting a bounce up) -> want CHOCH_UP.
    # RESISTANCE reached (expecting a rejection down) -> want CHOCH_DOWN.
    structure_event = detect_structure_event(bars_4h, params.confirm_swing_lookback)
    wanted_choch = "CHOCH_UP" if side == "SUPPORT" else "CHOCH_DOWN"
    checks.append(
        ConfirmationCheck(
            name="market_structure",
            passed=(structure_event == wanted_choch),
            detail=f"event={structure_event}, wanted={wanted_choch}",
        )
    )

    # 2. Liquidity sweep in our favor.
    sweep = detect_recent_liquidity_sweep(bars_4h, params.confirm_swing_lookback, params.confirm_sweep_reclaim_window)
    wanted_sweep_kind = "LOW" if side == "SUPPORT" else "HIGH"
    sweep_pass = sweep is not None and sweep.swept_kind == wanted_sweep_kind
    checks.append(
        ConfirmationCheck(
            name="liquidity_sweep",
            passed=sweep_pass,
            detail=f"swept={sweep.swept_kind if sweep else None}, wanted={wanted_sweep_kind}",
        )
    )

    # 3. FVG or order block nearby, in our favor.
    fvgs = detect_fair_value_gaps(bars_4h, params.confirm_fvg_lookback_bars)
    obs = detect_order_blocks(bars_4h, params.confirm_ob_lookback_bars)
    wanted_kind = "BULLISH" if side == "SUPPORT" else "BEARISH"
    tolerance = current_price * params.confirm_price_proximity_pct

    nearby_fvg = any(
        f.kind == wanted_kind and (f.gap_low - tolerance) <= current_price <= (f.gap_high + tolerance)
        for f in fvgs
    )
    nearby_ob = any(
        ob.kind == wanted_kind and (ob.low - tolerance) <= current_price <= (ob.high + tolerance)
        for ob in obs
    )
    checks.append(
        ConfirmationCheck(
            name="fvg_or_order_block",
            passed=(nearby_fvg or nearby_ob),
            detail=f"nearby_fvg={nearby_fvg}, nearby_ob={nearby_ob}, wanted_kind={wanted_kind}",
        )
    )

    # 4. Options positioning: meaningful OI concentration near price.
    oi_wall = (
        open_interest_wall_near(option_chain, current_price, params.confirm_oi_proximity_pct)
        if option_chain
        else 0
    )
    checks.append(
        ConfirmationCheck(
            name="options_positioning",
            passed=(oi_wall >= params.confirm_min_oi_wall),
            detail=f"oi_near_price={oi_wall}, min_required={params.confirm_min_oi_wall}",
        )
    )

    passed_count = sum(1 for c in checks if c.passed)
    confirmed = passed_count >= params.confirm_min_confirmations

    return ConfirmationResult(
        confirmed=confirmed,
        checks=checks,
        confirmations_passed=passed_count,
        confirmations_required=params.confirm_min_confirmations,
    )
