from datetime import UTC, datetime

import httpx
import pytest
import respx

from packages.ingestion.base import ProviderError
from packages.ingestion.providers.fred import FredProvider


@pytest.mark.asyncio
@respx.mock
async def test_get_history_parses_observations():
    payload = {
        "observations": [
            {"date": "2026-06-01", "value": "4.20"},
            {"date": "2026-06-02", "value": "4.25"},
        ]
    }
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=httpx.Response(200, json=payload)
    )

    provider = FredProvider(api_key="test-key")
    observations = await provider.get_history(
        "US10Y", datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 2, tzinfo=UTC)
    )

    assert len(observations) == 2
    assert observations[0].value == 4.20
    assert observations[0].source == "fred"
    assert observations[0].symbol == "US10Y"
    # available_at must not be before observed_at (release lag, never negative)
    assert observations[0].available_at >= observations[0].observed_at
    await provider.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_history_skips_missing_prints():
    payload = {
        "observations": [
            {"date": "2026-06-01", "value": "4.20"},
            {"date": "2026-06-02", "value": "."},  # FRED's missing-value marker
        ]
    }
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=httpx.Response(200, json=payload)
    )
    provider = FredProvider(api_key="test-key")
    observations = await provider.get_history(
        "US10Y", datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 2, tzinfo=UTC)
    )
    assert len(observations) == 1
    await provider.aclose()


@pytest.mark.asyncio
async def test_missing_api_key_raises_provider_error():
    provider = FredProvider(api_key=None)
    with pytest.raises(ProviderError):
        await provider.get_history(
            "US10Y", datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 2, tzinfo=UTC)
        )
    await provider.aclose()


@pytest.mark.asyncio
async def test_unsupported_symbol_raises_provider_error():
    provider = FredProvider(api_key="test-key")
    with pytest.raises(ProviderError):
        await provider.get_history(
            "NOT_A_SYMBOL", datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 2, tzinfo=UTC)
        )
    await provider.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_quote_returns_latest_observation():
    payload = {
        "observations": [
            {"date": "2026-06-01", "value": "4.20"},
            {"date": "2026-06-02", "value": "4.25"},
        ]
    }
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=httpx.Response(200, json=payload)
    )
    provider = FredProvider(api_key="test-key")
    quote = await provider.get_quote("US10Y")
    assert quote.value == 4.25
    await provider.aclose()
