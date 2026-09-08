from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.confirmation.engine import run_confirmation_engine
from src.config.strategy_params import StrategyParameters
from src.data.providers.base import Bar, OptionContract


def make_bars(rows: list[tuple[float, float, float, float]]) -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(symbol="TEST", timestamp=start + timedelta(hours=i), open=o, high=h, low=l, close=c, volume=1000)
        for i, (o, h, l, c) in enumerate(rows)
    ]


def make_contract(strike, call_put, oi=1000) -> OptionContract:
    return OptionContract(
        symbol="TEST",
        contract_symbol=f"TEST_{strike}_{call_put}",
        expiration=datetime.now(UTC) + timedelta(days=30),
        strike=strike,
        call_put=call_put,
        bid=1.0,
        ask=1.1,
        last=1.05,
        volume=100,
        open_interest=oi,
        implied_volatility=0.3,
    )


def test_engine_returns_all_four_checks():
    bars = make_bars([(100, 101, 99, 100)] * 10)
    result = run_confirmation_engine(bars, [], current_price=100, side="SUPPORT", params=StrategyParameters())
    assert len(result.checks) == 4
    assert {c.name for c in result.checks} == {
        "market_structure",
        "liquidity_sweep",
        "fvg_or_order_block",
        "options_positioning",
    }


def test_confirmed_requires_min_confirmations():
    bars = make_bars([(100, 101, 99, 100)] * 10)  # flat data -> no structure/sweep/fvg signals
    params = StrategyParameters(confirm_min_confirmations=1)
    chain = [make_contract(100, "CALL"), make_contract(100, "PUT")]  # heavy OI right at price -> passes check 4

    result = run_confirmation_engine(bars, chain, current_price=100, side="SUPPORT", params=params)
    assert result.confirmations_passed >= 1
    assert result.confirmed is True  # only needs 1 of 4


def test_not_confirmed_when_nothing_passes_and_threshold_is_high():
    bars = make_bars([(100, 101, 99, 100)] * 10)
    params = StrategyParameters(confirm_min_confirmations=4)

    result = run_confirmation_engine(bars, [], current_price=100, side="SUPPORT", params=params)
    assert result.confirmed is False


def test_options_positioning_check_uses_correct_side_agnostic_oi():
    bars = make_bars([(100, 101, 99, 100)] * 10)
    params = StrategyParameters(confirm_min_confirmations=1, confirm_min_oi_wall=100)
    chain = [make_contract(100, "PUT", oi=200)]

    result = run_confirmation_engine(bars, chain, current_price=100, side="RESISTANCE", params=params)
    options_check = next(c for c in result.checks if c.name == "options_positioning")
    assert options_check.passed is True
