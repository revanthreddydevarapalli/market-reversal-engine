"""
Basic OTM-liquid option picker (v1-lite scope).

This is intentionally simple: filter by DTE window and minimum
liquidity, then pick the contract closest to a target OTM distance from
the current underlying price. It is NOT the full multi-factor scoring
engine (delta/IV-rank/expected-move weighting) from the original master
spec -- that's deferred until deeper options analytics are built.

Treat the result as "a reasonably liquid contract worth looking at,"
never as a validated or guaranteed-best selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from src.data.providers.base import OptionContract

Direction = Literal["LONG_CALL", "LONG_PUT"]


@dataclass
class OptionPick:
    contract: OptionContract
    mid_price: float
    dte: int
    otm_pct: float


def pick_basic_otm_option(
    chain: list[OptionContract],
    current_price: float,
    direction: Direction,
    min_dte: int,
    max_dte: int,
    min_open_interest: int,
    min_volume: int,
    target_otm_pct: float,
    now: datetime | None = None,
) -> OptionPick | None:
    call_put = "CALL" if direction == "LONG_CALL" else "PUT"
    now = now or datetime.now(UTC)

    candidates: list[tuple[OptionContract, int, float]] = []
    for contract in chain:
        if contract.call_put != call_put:
            continue

        dte = (contract.expiration - now).days
        if not (min_dte <= dte <= max_dte):
            continue
        if contract.open_interest < min_open_interest or contract.volume < min_volume:
            continue
        if contract.bid <= 0 or contract.ask <= 0:
            continue

        is_otm = contract.strike > current_price if call_put == "CALL" else contract.strike < current_price
        if not is_otm:
            continue

        otm_pct = abs(contract.strike - current_price) / current_price
        candidates.append((contract, dte, otm_pct))

    if not candidates:
        return None

    best_contract, best_dte, best_otm_pct = min(
        candidates, key=lambda item: abs(item[2] - target_otm_pct)
    )
    mid_price = round((best_contract.bid + best_contract.ask) / 2, 2)

    return OptionPick(
        contract=best_contract, mid_price=mid_price, dte=best_dte, otm_pct=round(best_otm_pct, 4)
    )
