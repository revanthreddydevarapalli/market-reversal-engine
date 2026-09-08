from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JournalEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    symbol: str
    side: str
    status: str
    current_price: float
    zone_low: float
    zone_high: float
    zone_center: float
    strength_stars: int
    timeframes_present: list[str]
    level_types_present: list[str]
    option_call_put: str | None
    option_strike: float | None
    option_expiration: str | None
    option_dte: int | None
    option_mid_price: float | None
    option_otm_pct: float | None
    option_contract_symbol: str | None
    option_status: str
    strategy_version: str
