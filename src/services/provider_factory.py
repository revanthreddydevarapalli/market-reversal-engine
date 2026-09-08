"""Builds concrete provider instances from Settings. Kept separate from
`services/reversal_service.py` so that module stays provider-agnostic
and testable with fakes."""

from __future__ import annotations

from src.config.settings import Settings
from src.data.providers.tradingview.client import TradingViewScraperProvider


def build_ohlcv_provider(settings: Settings) -> TradingViewScraperProvider:
    return TradingViewScraperProvider(base_url=settings.tradingview_scraper_base_url)


def build_options_provider():
    # Imported lazily: yfinance is a heavier optional dependency, and a
    # module-level function reference is enough for the options-provider
    # Protocol (get_option_chain(symbol)).
    from src.data.providers.yfinance.options import get_option_chain

    class _YFinanceOptionsProvider:
        def get_option_chain(self, symbol: str):
            return get_option_chain(symbol)

    return _YFinanceOptionsProvider()
