"""GET /levels/{symbol} -- the simplified, public-facing output: the
top support zones (below current price) and top resistance zones
(above current price), each with a star rating, status, and -- for any
REACHED zone -- the full entry-confirmation breakdown (see
src/confirmation/engine.py) plus a basic liquid OTM option suggestion
if that zone passed confirmation.

As a side effect, any zone found REACHED is logged to the trade
journal (deduplicated -- see services/journal_service.py) so there's a
persistent record even though this endpoint itself is read-only/
on-demand.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.config.strategy_params import DEFAULT_STRATEGY_PARAMETERS, StrategyParameters
from src.database.session import get_db
from src.schemas.levels import (
    ConfirmationCheckResponse,
    ConfirmationResultResponse,
    OptionPickResponse,
    SymbolLevelResponse,
    ZoneResponse,
)
from src.services.journal_service import log_reached_zones
from src.services.provider_factory import build_ohlcv_provider, build_options_provider
from src.services.reversal_service import SymbolAnalysis, ZoneAnalysis, analyze_symbol

router = APIRouter(tags=["levels"])


def _zone_analysis_to_response(analysis: ZoneAnalysis) -> ZoneResponse:
    option = None
    if analysis.option_pick is not None:
        pick = analysis.option_pick
        option = OptionPickResponse(
            call_put=pick.contract.call_put,
            strike=pick.contract.strike,
            expiration=pick.contract.expiration.date().isoformat(),
            dte=pick.dte,
            mid_price=pick.mid_price,
            otm_pct=pick.otm_pct,
            contract_symbol=pick.contract.contract_symbol,
        )

    confirmation = None
    if analysis.confirmation is not None:
        confirmation = ConfirmationResultResponse(
            confirmed=analysis.confirmation.confirmed,
            confirmations_passed=analysis.confirmation.confirmations_passed,
            confirmations_required=analysis.confirmation.confirmations_required,
            checks=[
                ConfirmationCheckResponse(name=c.name, passed=c.passed, detail=c.detail)
                for c in analysis.confirmation.checks
            ],
        )

    return ZoneResponse(
        side=analysis.side,
        zone_low=round(analysis.zone.lower, 2),
        zone_high=round(analysis.zone.upper, 2),
        center=round(analysis.zone.center, 2),
        distance_pct=round(analysis.distance_pct, 4),
        strength_stars=analysis.zone.strength_stars,
        status=analysis.status,
        timeframes_present=sorted(analysis.zone.timeframes_present),
        level_types_present=sorted(analysis.zone.level_types_present),
        confirmation=confirmation,
        option=option,
        option_status=analysis.option_status,
    )


@router.get("/levels/{symbol}", response_model=SymbolLevelResponse)
def get_symbol_levels(
    symbol: str,
    top_n: int = Query(default=10, ge=1, le=30, description="Max zones to return per side"),
    bin_count: int | None = Query(default=None, gt=0, description="Override profile bin count"),
    hvn_lvn_window: int | None = Query(default=None, gt=0, description="Override HVN/LVN neighborhood window"),
    hvn_lvn_min_prominence_pct: float | None = Query(
        default=None, ge=0, description="Override HVN/LVN prominence threshold (lower = more sensitive)"
    ),
    cluster_tolerance_pct: float | None = Query(
        default=None, gt=0, description="Override confluence clustering tolerance"
    ),
    trend_lookback_bars: int | None = Query(
        default=None, gt=0, description="Override trend lookback (in 1D bars)"
    ),
    trend_flat_threshold_pct: float | None = Query(
        default=None, ge=0, description="Override trend FLAT threshold"
    ),
    confirm_min_confirmations: int | None = Query(
        default=None, ge=0, le=4, description="Override how many of the 4 confirmation checks must pass"
    ),
    db: Session = Depends(get_db),
) -> SymbolLevelResponse:
    settings = get_settings()
    ohlcv_provider = build_ohlcv_provider(settings)
    options_provider = build_options_provider()

    overrides = {
        k: v
        for k, v in {
            "bin_count": bin_count,
            "hvn_lvn_window": hvn_lvn_window,
            "hvn_lvn_min_prominence_pct": hvn_lvn_min_prominence_pct,
            "cluster_tolerance_pct": cluster_tolerance_pct,
            "trend_lookback_bars": trend_lookback_bars,
            "trend_flat_threshold_pct": trend_flat_threshold_pct,
            "confirm_min_confirmations": confirm_min_confirmations,
        }.items()
        if v is not None
    }
    params: StrategyParameters = (
        DEFAULT_STRATEGY_PARAMETERS.model_copy(update=overrides) if overrides else DEFAULT_STRATEGY_PARAMETERS
    )

    try:
        analysis: SymbolAnalysis = analyze_symbol(
            symbol=symbol.upper(),
            ohlcv_provider=ohlcv_provider,
            options_provider=options_provider,
            params=params,
            top_n_per_side=top_n,
        )
    except Exception as exc:  # noqa: BLE001 -- surfaced as a clean 502 for now
        raise HTTPException(
            status_code=502, detail=f"Failed to analyze {symbol}: {exc}"
        ) from exc

    try:
        log_reached_zones(db, analysis, params)
    except Exception:  # noqa: BLE001 -- journal logging must never break the read path
        db.rollback()

    return SymbolLevelResponse(
        symbol=analysis.symbol,
        current_price=round(analysis.current_price, 2),
        trend=analysis.trend,
        support_levels=[_zone_analysis_to_response(z) for z in analysis.support_zones],
        resistance_levels=[_zone_analysis_to_response(z) for z in analysis.resistance_zones],
    )
