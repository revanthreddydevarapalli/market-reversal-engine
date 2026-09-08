from unittest.mock import MagicMock, patch

from src.data.providers.tradingview.client import TradingViewScraperProvider


SAMPLE_PAYLOAD = {
    "status": "success",
    "total": 2,
    "data": [
        {"index": 1, "timestamp": 1712620800, "open": 170.0, "high": 171.0, "low": 169.5, "close": 170.5, "volume": 1000},
        {"index": 0, "timestamp": 1712534400, "open": 169.59, "high": 170.15, "low": 168.32, "close": 169.60, "volume": 42051200},
    ],
}


@patch("src.data.providers.tradingview.client.requests.get")
def test_get_ohlcv_parses_and_sorts_by_timestamp(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_PAYLOAD
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    provider = TradingViewScraperProvider(base_url="http://localhost:8100")
    bars = provider.get_ohlcv("NVDA", "1D", limit=100)

    assert len(bars) == 2
    # Sorted ascending by timestamp despite payload being out of order.
    assert bars[0].timestamp < bars[1].timestamp
    assert bars[0].close == 169.60
    assert bars[1].close == 170.5

    called_url = mock_get.call_args.args[0]
    assert called_url == "http://localhost:8100/api/ohlcv/NASDAQ/NVDA"
    assert mock_get.call_args.kwargs["params"] == {"timeframe": "1d", "candles": 100}


@patch("src.data.providers.tradingview.client.requests.get")
def test_futures_symbol_uses_mapped_exchange(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "success", "total": 0, "data": []}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    provider = TradingViewScraperProvider(base_url="http://localhost:8100")
    provider.get_ohlcv("ES", "4H", limit=50)

    called_url = mock_get.call_args.args[0]
    assert called_url == "http://localhost:8100/api/ohlcv/CME_MINI/ES"
    assert mock_get.call_args.kwargs["params"]["timeframe"] == "4h"


def test_unsupported_timeframe_raises():
    import pytest

    provider = TradingViewScraperProvider(base_url="http://localhost:8100")
    with pytest.raises(ValueError):
        provider.get_ohlcv("NVDA", "1M", limit=10)  # type: ignore[arg-type]


@patch("src.data.providers.tradingview.client.requests.get")
def test_handles_dict_wrapped_response_shape(mock_get):
    """Regression test: the live service wraps rows in
    {"status": "success", "data": [...], "total": N}, not a bare list
    as the upstream README's top-level example suggested."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "total": 1,
        "data": [{"index": 0, "timestamp": 1788355800, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10}],
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    provider = TradingViewScraperProvider(base_url="http://localhost:8100")
    bars = provider.get_ohlcv("NVDA", "1D", limit=10)

    assert len(bars) == 1
    assert bars[0].close == 1.5
