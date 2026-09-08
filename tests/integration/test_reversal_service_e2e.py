from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.config.strategy_params import StrategyParameters
from src.data.providers.base import Bar, OptionContract
from src.services.reversal_service import analyze_symbol


class FakeOHLCVProvider:
    """Builds a synthetic price series with a clear volume cluster around
    177 across all three timeframes, so a confluence zone is guaranteed
    and current price sits inside it (status should be REACHED)."""

    def get_ohlcv(self, symbol, timeframe, limit=500):
        start = datetime(2026, 1, 1, tzinfo=UTC)
        bars = []
        # Most bars trade in a tight range around 177 with high volume;
        # a few bars range wider with low volume, to create HVN/LVN texture.
        rows = [
            (170.0, 172.0, 169.0, 171.0, 300),
            (185.0, 187.0, 184.0, 186.0, 250),
            (176.5, 177.5, 176.0, 177.2, 5000),
            (177.0, 177.6, 176.8, 177.3, 6000),
            (177.2, 177.8, 177.0, 177.5, 5500),
            (177.2, 177.9, 177.1, 177.0, 5200),  # most recent bar (close lands inside the confluence zone)
        ]
        for i, (o, h, low, c, v) in enumerate(rows):
            bars.append(
                Bar(symbol=symbol, timestamp=start + timedelta(hours=i), open=o, high=h, low=low, close=c, volume=v)
            )
        return bars


class FakeOptionsProvider:
    def get_option_chain(self, symbol):
        expiration = datetime.now(UTC) + timedelta(days=30)
        return [
            OptionContract(
                symbol=symbol,
                contract_symbol=f"{symbol}_180C",
                expiration=expiration,
                strike=182.0,
                call_put="CALL",
                bid=3.0,
                ask=3.2,
                last=3.1,
                volume=500,
                open_interest=1000,
                implied_volatility=0.4,
            ),
            OptionContract(
                symbol=symbol,
                contract_symbol=f"{symbol}_170P",
                expiration=expiration,
                strike=172.0,
                call_put="PUT",
                bid=2.0,
                ask=2.2,
                last=2.1,
                volume=400,
                open_interest=800,
                implied_volatility=0.4,
            ),
        ]


def test_analyze_symbol_end_to_end_reaches_zone_and_picks_option_when_confirmed():
    # confirm_min_confirmations=0 isolates the reached->option-pick wiring
    # from the confirmation logic itself, which has its own dedicated
    # unit tests in tests/unit/confirmation/.
    params = StrategyParameters(
        bin_count=30, hvn_lvn_window=2, hvn_lvn_min_prominence_pct=0.1, confirm_min_confirmations=0
    )

    result = analyze_symbol(
        symbol="NVDA",
        ohlcv_provider=FakeOHLCVProvider(),
        options_provider=FakeOptionsProvider(),
        params=params,
    )

    assert result.symbol == "NVDA"
    all_zones = result.support_zones + result.resistance_zones
    assert len(all_zones) > 0

    reached = [z for z in all_zones if z.status == "REACHED"]
    assert len(reached) >= 1
    assert reached[0].confirmation is not None
    assert reached[0].confirmation.confirmed is True  # threshold=0 -> always confirmed
    assert reached[0].option_status == "OK"
    assert reached[0].option_pick is not None
    assert reached[0].option_pick.contract.call_put in ("CALL", "PUT")


def test_reached_zone_without_confirmation_does_not_get_an_option():
    # Default confirm_min_confirmations (2) with plain/flat fixture data
    # that shouldn't trip structure/sweep/fvg signals -> NOT_CONFIRMED,
    # no option suggested even though the zone was reached.
    params = StrategyParameters(bin_count=30, hvn_lvn_window=2, hvn_lvn_min_prominence_pct=0.1)

    result = analyze_symbol(
        symbol="NVDA",
        ohlcv_provider=FakeOHLCVProvider(),
        options_provider=FakeOptionsProvider(),
        params=params,
    )

    all_zones = result.support_zones + result.resistance_zones
    reached = [z for z in all_zones if z.status == "REACHED"]
    assert len(reached) >= 1
    assert reached[0].confirmation is not None
    if not reached[0].confirmation.confirmed:
        assert reached[0].option_pick is None
        assert reached[0].option_status == "NOT_CONFIRMED"

    # Support zones should genuinely sit below price, resistance above.
    for z in result.support_zones:
        assert z.side == "SUPPORT"
    for z in result.resistance_zones:
        assert z.side == "RESISTANCE"


def test_analyze_symbol_without_options_provider_reports_status():
    # confirm_min_confirmations=0 isolates the "no provider" behavior
    # from confirmation gating (already tested separately above).
    params = StrategyParameters(
        bin_count=30, hvn_lvn_window=2, hvn_lvn_min_prominence_pct=0.1, confirm_min_confirmations=0
    )

    result = analyze_symbol(
        symbol="NVDA",
        ohlcv_provider=FakeOHLCVProvider(),
        options_provider=None,
        params=params,
    )

    all_zones = result.support_zones + result.resistance_zones
    reached = [z for z in all_zones if z.status == "REACHED"]
    assert len(reached) >= 1
    assert reached[0].option_pick is None
    assert reached[0].option_status == "OPTIONS_PROVIDER_UNAVAILABLE"


def test_zones_are_ranked_strongest_first_on_each_side():
    params = StrategyParameters(bin_count=30, hvn_lvn_window=2, hvn_lvn_min_prominence_pct=0.1)

    result = analyze_symbol(
        symbol="NVDA",
        ohlcv_provider=FakeOHLCVProvider(),
        options_provider=None,
        params=params,
    )

    for zones in (result.support_zones, result.resistance_zones):
        scores = [z.zone.base_score for z in zones]
        assert scores == sorted(scores, reverse=True)
