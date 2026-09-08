"""
Public-facing response schemas. Surfaces both sides of price (support
below, resistance above), a simple `trend` field, and -- for any
REACHED zone -- the full breakdown of the entry confirmation engine
(see src/confirmation/engine.py): which checks passed/failed and
whether the zone was CONFIRMED enough to get an option suggestion.

This is a deterministic checklist, explicitly not backtested or
statistically validated. See CLAUDE.md.
"""

from __future__ import annotations

from pydantic import BaseModel


class OptionPickResponse(BaseModel):
    call_put: str
    strike: float
    expiration: str
    dte: int
    mid_price: float
    otm_pct: float
    contract_symbol: str


class ConfirmationCheckResponse(BaseModel):
    name: str
    passed: bool
    detail: str


class ConfirmationResultResponse(BaseModel):
    confirmed: bool
    confirmations_passed: int
    confirmations_required: int
    checks: list[ConfirmationCheckResponse]


class ZoneResponse(BaseModel):
    side: str  # SUPPORT | RESISTANCE
    zone_low: float
    zone_high: float
    center: float
    distance_pct: float
    strength_stars: int
    status: str  # WAITING | NEAR | REACHED
    timeframes_present: list[str]
    level_types_present: list[str]
    confirmation: ConfirmationResultResponse | None  # only present when status == REACHED
    option: OptionPickResponse | None
    option_status: str


class SymbolLevelResponse(BaseModel):
    symbol: str
    current_price: float
    trend: str  # UP | DOWN | FLAT -- crude momentum heuristic, see src/trend/trend.py
    support_levels: list[ZoneResponse]     # below current price, strongest first
    resistance_levels: list[ZoneResponse]  # above current price, strongest first
