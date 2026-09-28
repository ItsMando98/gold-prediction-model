from datetime import UTC, datetime

import httpx
import pytest
import respx

from packages.ingestion.base import ProviderError
from packages.ingestion.providers.cftc_cot import CftcCotProvider


def _row(date: str, mm_long: str, mm_short: str, oi: str = "500000") -> dict:
    return {
        "report_date_as_yyyy_mm_dd": f"{date}T00:00:00.000",
        "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
        "open_interest_all": oi,
        "m_money_positions_long_all": mm_long,
        "m_money_positions_short_all": mm_short,
        "prod_merc_positions_long_all": "80000",
        "prod_merc_positions_short_all": "120000",
        "swap_positions_long_all": "40000",
        "swap__positions_short_all": "30000",
        "other_rept_positions_long_all": "50000",
        "other_rept_positions_short_all": "45000",
    }


@pytest.mark.asyncio
@respx.mock
async def test_get_history_parses_rows_and_sets_friday_release():
    rows = [_row("2026-06-02", "200000", "40000"), _row("2026-06-09", "205000", "38000")]
    respx.get("https://publicreporting.cftc.gov/resource/72hh-3qpy.json").mock(
        return_value=httpx.Response(200, json=rows)
    )

    provider = CftcCotProvider()
    start, end = datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 10, tzinfo=UTC)
    records = await provider.get_history("GC", start, end)

    assert len(records) == 2
    first = records[0]
    assert first.observed_at == datetime(2026, 6, 2, tzinfo=UTC)
    # 2026-06-02 is a Tuesday -> report released the following Friday, 2026-06-05
    assert first.available_at == datetime(2026, 6, 5, 19, 30, tzinfo=UTC)
    assert first.managed_money_long == 200000.0
    assert first.managed_money_short == 40000.0
    assert first.open_interest == 500000.0
    await provider.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_history_handles_missing_optional_fields():
    row = _row("2026-06-02", "200000", "40000")
    del row["swap_positions_long_all"]
    respx.get("https://publicreporting.cftc.gov/resource/72hh-3qpy.json").mock(
        return_value=httpx.Response(200, json=[row])
    )
    provider = CftcCotProvider()
    start, end = datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 10, tzinfo=UTC)
    records = await provider.get_history("GC", start, end)
    assert records[0].swap_dealer_long is None
    await provider.aclose()


@pytest.mark.asyncio
async def test_unsupported_symbol_raises_provider_error():
    provider = CftcCotProvider()
    with pytest.raises(ProviderError):
        await provider.get_history(
            "NOT_A_SYMBOL", datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 10, tzinfo=UTC)
        )
    await provider.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_history_raises_on_malformed_report_date():
    respx.get("https://publicreporting.cftc.gov/resource/72hh-3qpy.json").mock(
        return_value=httpx.Response(200, json=[{"report_date_as_yyyy_mm_dd": "not-a-date"}])
    )
    provider = CftcCotProvider()
    with pytest.raises(ProviderError):
        await provider.get_history("GC", datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 10, tzinfo=UTC))
    await provider.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_history_raises_on_http_error():
    respx.get("https://publicreporting.cftc.gov/resource/72hh-3qpy.json").mock(
        return_value=httpx.Response(500)
    )
    provider = CftcCotProvider()
    with pytest.raises(ProviderError):
        await provider.get_history("GC", datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 10, tzinfo=UTC))
    await provider.aclose()
