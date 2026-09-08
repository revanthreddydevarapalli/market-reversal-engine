from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.confirmation.options_positioning import black_scholes_gamma, compute_gamma_walls, open_interest_wall_near
from src.data.providers.base import OptionContract


def make_contract(strike, call_put, dte, oi, iv=0.3) -> OptionContract:
    return OptionContract(
        symbol="TEST",
        contract_symbol=f"TEST_{strike}_{call_put}",
        expiration=datetime.now(UTC) + timedelta(days=dte),
        strike=strike,
        call_put=call_put,
        bid=1.0,
        ask=1.1,
        last=1.05,
        volume=100,
        open_interest=oi,
        implied_volatility=iv,
    )


def test_gamma_is_highest_near_the_money():
    atm_gamma = black_scholes_gamma(spot=100, strike=100, time_to_expiry_years=30 / 365, iv=0.3)
    otm_gamma = black_scholes_gamma(spot=100, strike=150, time_to_expiry_years=30 / 365, iv=0.3)
    assert atm_gamma > otm_gamma > 0


def test_gamma_is_zero_for_invalid_inputs():
    assert black_scholes_gamma(spot=0, strike=100, time_to_expiry_years=0.1, iv=0.3) == 0.0
    assert black_scholes_gamma(spot=100, strike=100, time_to_expiry_years=0, iv=0.3) == 0.0
    assert black_scholes_gamma(spot=100, strike=100, time_to_expiry_years=0.1, iv=0) == 0.0


def test_gamma_walls_sorted_by_magnitude():
    chain = [
        make_contract(100, "CALL", 30, oi=1000),
        make_contract(105, "CALL", 30, oi=10),
        make_contract(100, "PUT", 30, oi=1000),
    ]
    walls = compute_gamma_walls(chain, spot=100)
    assert len(walls) >= 1
    magnitudes = [abs(w.net_gamma_exposure) for w in walls]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_gamma_walls_skip_contracts_without_iv():
    chain = [make_contract(100, "CALL", 30, oi=1000, iv=None)]
    assert compute_gamma_walls(chain, spot=100) == []


def test_open_interest_wall_near_sums_calls_and_puts_within_tolerance():
    chain = [
        make_contract(100, "CALL", 30, oi=500),
        make_contract(100, "PUT", 30, oi=300),
        make_contract(150, "CALL", 30, oi=9999),  # far away, excluded
    ]
    total = open_interest_wall_near(chain, price=100, tolerance_pct=0.02)
    assert total == 800


def test_open_interest_wall_near_zero_price_returns_zero():
    assert open_interest_wall_near([make_contract(100, "CALL", 30, oi=500)], price=0) == 0
