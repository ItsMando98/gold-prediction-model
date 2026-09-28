"""CFTC Disaggregated Commitment of Traders provider (plan section 12).

Covers GC (gold) and SILVER via the public Socrata API, no API key
required. Requires outbound HTTPS to ``publicreporting.cftc.gov`` -- not
available from every environment (e.g. this repo's sandbox), so this
module is unit-tested against mocked HTTP responses rather than live
calls.

**Field names below are the CFTC Disaggregated Futures-Only report's
documented Socrata column names (dataset ``72hh-3qpy``) as of this
writing, not verified against a live response from this sandbox** (no
network access to confirm). Before relying on this in production, hit
``https://publicreporting.cftc.gov/resource/72hh-3qpy.json?$limit=1`` and
confirm the field names still match; CFTC has renamed columns on this
dataset before.

Availability timing: the COT report is published every Friday at 15:30 ET
for data as of the prior Tuesday's close. ``available_at`` is fixed at the
Friday following ``observed_at`` (the report date), not the report date
itself -- using the report date for point-in-time reads would leak future
positioning data into a backtest.
"""

from datetime import UTC, datetime, time, timedelta

import httpx

from packages.common.schemas import CotRecord
from packages.ingestion.base import PositioningProvider, ProviderError
from packages.ingestion.symbol_map import get_ticker, supported_symbols

_BASE_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
_REPORT_RELEASE_TIME = time(hour=19, minute=30)  # UTC, ~15:30 US/Eastern


def _next_friday_release(report_date: datetime) -> datetime:
    days_until_friday = (4 - report_date.weekday()) % 7
    days_until_friday = days_until_friday or 7  # report_date is itself a Tuesday; force forward
    release_date = report_date.date() + timedelta(days=days_until_friday)
    return datetime.combine(release_date, _REPORT_RELEASE_TIME, tzinfo=UTC)


def _to_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class CftcCotProvider(PositioningProvider):
    name = "cftc_cot"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=20.0)

    def supports(self, symbol: str) -> bool:
        return symbol in supported_symbols(self.name)

    def _market_name(self, symbol: str) -> str:
        market_name = get_ticker(self.name, symbol)
        if market_name is None:
            raise ProviderError(self.name, f"no CFTC market mapping for symbol {symbol!r}")
        return market_name

    async def get_history(self, symbol: str, start: datetime, end: datetime) -> list[CotRecord]:
        market_name = self._market_name(symbol)
        where = (
            f"market_and_exchange_names='{market_name}' AND "
            f"report_date_as_yyyy_mm_dd between '{start.strftime('%Y-%m-%d')}T00:00:00' "
            f"and '{end.strftime('%Y-%m-%d')}T23:59:59'"
        )
        params = {"$where": where, "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": "5000"}

        try:
            response = await self._client.get(_BASE_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(self.name, f"request failed for {market_name}: {exc}", cause=exc) from exc

        rows = response.json()
        if not isinstance(rows, list):
            raise ProviderError(self.name, f"malformed response for {market_name}")

        now = datetime.now(UTC)
        records: list[CotRecord] = []
        for row in rows:
            try:
                report_date = datetime.strptime(
                    row["report_date_as_yyyy_mm_dd"][:10], "%Y-%m-%d"
                ).replace(tzinfo=UTC)
            except (KeyError, ValueError) as exc:
                raise ProviderError(
                    self.name, f"malformed report_date in row for {market_name}: {row!r}", cause=exc
                ) from exc

            records.append(
                CotRecord(
                    source=self.name,
                    symbol=symbol,
                    observed_at=report_date,
                    available_at=_next_friday_release(report_date),
                    ingested_at=now,
                    open_interest=_to_float(row.get("open_interest_all")),
                    managed_money_long=_to_float(row.get("m_money_positions_long_all")),
                    managed_money_short=_to_float(row.get("m_money_positions_short_all")),
                    producer_long=_to_float(row.get("prod_merc_positions_long_all")),
                    producer_short=_to_float(row.get("prod_merc_positions_short_all")),
                    swap_dealer_long=_to_float(row.get("swap_positions_long_all")),
                    swap_dealer_short=_to_float(row.get("swap__positions_short_all")),
                    other_reportable_long=_to_float(row.get("other_rept_positions_long_all")),
                    other_reportable_short=_to_float(row.get("other_rept_positions_short_all")),
                    metadata={"market_and_exchange_names": market_name},
                )
            )
        return records

    async def aclose(self) -> None:
        await self._client.aclose()
