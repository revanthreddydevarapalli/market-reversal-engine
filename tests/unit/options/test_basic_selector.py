from datetime import UTC, datetime, timedelta

from src.data.providers.base import OptionContract
from src.options.basic_selector import pick_basic_otm_option


NOW = datetime(2026, 1, 1, tzinfo=UTC)


def make_contract(strike, call_put, dte, bid, ask, oi, volume) -> OptionContract:
    return OptionContract(
        symbol="NVDA",
        contract_symbol=f"NVDA_{strike}_{call_put}",
        expiration=NOW + timedelta(days=dte),
        strike=strike,
        call_put=call_put,
        bid=bid,
        ask=ask,
        last=None,
        volume=volume,
        open_interest=oi,
        implied_volatility=None,
    )


def test_picks_closest_liquid_contract_to_target_otm():
    # current_price=177, target_otm_pct=0.03 (~5.31 above price, i.e. ~182.3)
    chain = [
        make_contract(180, "CALL", 30, 4.0, 4.2, 500, 100),   # ~1.7% OTM -> |1.7-3| = 1.3
        make_contract(185, "CALL", 30, 2.5, 2.7, 400, 80),    # ~4.5% OTM -> |4.5-3| = 1.5
        make_contract(183, "CALL", 30, 3.0, 3.2, 300, 60),    # ~3.4% OTM -> |3.4-3| = 0.4  <- closest
        make_contract(200, "CALL", 30, 0.5, 0.6, 50, 5),      # illiquid, far OTM
        make_contract(170, "CALL", 30, 8.0, 8.2, 300, 50),    # ITM, excluded
    ]

    pick = pick_basic_otm_option(
        chain,
        current_price=177.0,
        direction="LONG_CALL",
        min_dte=14,
        max_dte=45,
        min_open_interest=100,
        min_volume=10,
        target_otm_pct=0.03,
        now=NOW,
    )

    assert pick is not None
    assert pick.contract.strike == 183
    assert pick.mid_price == 3.1


def test_excludes_illiquid_contracts():
    chain = [make_contract(180, "CALL", 30, 4.0, 4.2, 5, 1)]  # below liquidity thresholds

    pick = pick_basic_otm_option(
        chain,
        current_price=177.0,
        direction="LONG_CALL",
        min_dte=14,
        max_dte=45,
        min_open_interest=100,
        min_volume=10,
        target_otm_pct=0.03,
        now=NOW,
    )

    assert pick is None


def test_excludes_out_of_dte_window():
    chain = [make_contract(180, "CALL", 5, 4.0, 4.2, 500, 100)]  # DTE too short

    pick = pick_basic_otm_option(
        chain,
        current_price=177.0,
        direction="LONG_CALL",
        min_dte=14,
        max_dte=45,
        min_open_interest=100,
        min_volume=10,
        target_otm_pct=0.03,
        now=NOW,
    )

    assert pick is None


def test_put_direction_requires_strike_below_price():
    chain = [
        make_contract(175, "PUT", 30, 3.0, 3.2, 500, 100),  # OTM put
        make_contract(180, "PUT", 30, 6.0, 6.2, 500, 100),  # ITM put, excluded
    ]

    pick = pick_basic_otm_option(
        chain,
        current_price=177.0,
        direction="LONG_PUT",
        min_dte=14,
        max_dte=45,
        min_open_interest=100,
        min_volume=10,
        target_otm_pct=0.03,
        now=NOW,
    )

    assert pick is not None
    assert pick.contract.strike == 175
