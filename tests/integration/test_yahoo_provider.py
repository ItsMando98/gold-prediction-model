from datetime import UTC, datetime

import httpx
import pytest
import respx

from packages.ingestion.base import ProviderError
from packages.ingestion.providers.yahoo_finance import YahooFinanceProvider


def _chart_payload(timestamps, opens, highs, lows, closes, volumes):
    return {
        "chart": {
            "result": [
                {
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


@pytest.mark.asyncio
@respx.mock
async def test_get_history_parses_bars():
    ts = [1749081600, 1749168000]  # two daily bars
    payload = _chart_payload(
        ts, [2000.0, 2010.0], [2015.0, 2020.0], [1995.0, 2005.0], [2010.0, 2015.0], [1000, 1100]
    )
    respx.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F").mock(
        return_value=httpx.Response(200, json=payload)
    )

    provider = YahooFinanceProvider()
    start, end = datetime(2025, 6, 5, tzinfo=UTC), datetime(2025, 6, 6, tzinfo=UTC)
    bars = await provider.get_history("GC", start, end)

    assert len(bars) == 2
    assert bars[0].close == 2010.0
    assert bars[0].source == "yahoo_finance"
    assert bars[0].symbol == "GC"
    assert bars[0].metadata["vendor_ticker"] == "GC=F"
    await provider.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_history_skips_null_bars_on_holidays():
    ts = [1749081600, 1749168000]
    payload = _chart_payload(ts, [2000.0, None], [2015.0, None], [1995.0, None], [2010.0, None], [1000, None])
    respx.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F").mock(
        return_value=httpx.Response(200, json=payload)
    )

    provider = YahooFinanceProvider()
    start, end = datetime(2025, 6, 5, tzinfo=UTC), datetime(2025, 6, 6, tzinfo=UTC)
    bars = await provider.get_history("GC", start, end)

    assert len(bars) == 1
    await provider.aclose()


@pytest.mark.asyncio
async def test_supports_only_configured_symbols():
    provider = YahooFinanceProvider()
    assert provider.supports("GC") is True
    assert provider.supports("NOT_A_SYMBOL") is False
    await provider.aclose()


@pytest.mark.asyncio
async def test_unsupported_symbol_raises_provider_error():
    provider = YahooFinanceProvider()
    with pytest.raises(ProviderError):
        await provider.get_history(
            "NOT_A_SYMBOL", datetime(2025, 6, 5, tzinfo=UTC), datetime(2025, 6, 6, tzinfo=UTC)
        )
    await provider.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_history_raises_on_http_error():
    respx.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F").mock(
        return_value=httpx.Response(500)
    )
    provider = YahooFinanceProvider()
    with pytest.raises(ProviderError):
        await provider.get_history("GC", datetime(2025, 6, 5, tzinfo=UTC), datetime(2025, 6, 6, tzinfo=UTC))
    await provider.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_quote_returns_latest_bar():
    ts = [1749081600, 1749168000]
    payload = _chart_payload(
        ts, [2000.0, 2010.0], [2015.0, 2020.0], [1995.0, 2005.0], [2010.0, 2015.0], [1000, 1100]
    )
    respx.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F").mock(
        return_value=httpx.Response(200, json=payload)
    )
    provider = YahooFinanceProvider()
    quote = await provider.get_quote("GC")
    assert quote.close == 2015.0
    await provider.aclose()
