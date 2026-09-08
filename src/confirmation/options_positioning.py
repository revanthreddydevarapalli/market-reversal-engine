"""
Options-positioning based confirmation signals.

IMPORTANT LIMITATION: true dealer gamma exposure (GEX) requires knowing
market makers' actual net position (long or short) per contract, which
is proprietary and unavailable outside the dealers themselves. What's
computed here is a common retail-quant APPROXIMATION: it assumes
customers are net long the calls and puts they trade against dealers
(a common simplifying assumption, not universally true), computes each
contract's Black-Scholes gamma from its public implied volatility, and
aggregates by strike weighted by public open interest as a proxy for
position size. Treat this as "where is options exposure concentrated,"
not a confirmed measure of real dealer hedging flows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from src.data.providers.base import OptionContract


@dataclass(frozen=True)
class GammaWall:
    strike: float
    net_gamma_exposure: float  # signed, approximate -- see module docstring


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def black_scholes_gamma(
    spot: float, strike: float, time_to_expiry_years: float, iv: float, risk_free_rate: float = 0.04
) -> float:
    if spot <= 0 or strike <= 0 or time_to_expiry_years <= 0 or iv <= 0:
        return 0.0
    d1 = (
        math.log(spot / strike) + (risk_free_rate + 0.5 * iv * iv) * time_to_expiry_years
    ) / (iv * math.sqrt(time_to_expiry_years))
    return _norm_pdf(d1) / (spot * iv * math.sqrt(time_to_expiry_years))


def compute_gamma_walls(
    chain: list[OptionContract], spot: float, now: datetime | None = None
) -> list[GammaWall]:
    """Aggregate approximate net gamma exposure per strike, sorted by
    magnitude descending (largest walls first). See module docstring
    for the approximation this relies on."""
    now = now or datetime.now(UTC)
    by_strike: dict[float, float] = {}

    for contract in chain:
        if contract.implied_volatility is None or contract.implied_volatility <= 0:
            continue
        time_to_expiry = (contract.expiration - now).days / 365.0
        if time_to_expiry <= 0:
            continue

        gamma = black_scholes_gamma(spot, contract.strike, time_to_expiry, contract.implied_volatility)
        dollar_gamma = gamma * contract.open_interest * 100 * spot * spot * 0.01
        sign = 1.0 if contract.call_put == "CALL" else -1.0
        by_strike[contract.strike] = by_strike.get(contract.strike, 0.0) + sign * dollar_gamma

    walls = [GammaWall(strike=k, net_gamma_exposure=v) for k, v in by_strike.items()]
    walls.sort(key=lambda w: abs(w.net_gamma_exposure), reverse=True)
    return walls


def open_interest_wall_near(chain: list[OptionContract], price: float, tolerance_pct: float = 0.02) -> int:
    """Total open interest (calls + puts combined) at strikes within
    tolerance_pct of the given price -- a simple concentration proxy,
    independent of the GEX approximation above."""
    if price <= 0:
        return 0
    return sum(c.open_interest for c in chain if abs(c.strike - price) / price <= tolerance_pct)
