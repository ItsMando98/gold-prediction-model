"""FRED (Federal Reserve Economic Data) provider for rates / yields.

Covers US02Y, US05Y, US10Y and the US10Y real yield (plan section 8).
Requires ``FRED_API_KEY`` and outbound HTTPS access to
``api.stlouisfed.org`` -- not available from every environment (e.g. this
repo's sandbox), so this module is unit-tested against mocked HTTP
responses rather than live calls.

Availability timing: FRED's daily H.15 constant-maturity yield series are
posted the same business day, in the evening (US Treasury / Fed release
schedule). We approximate ``available_at`` as 21:30 UTC on the observation
date (~16:30 US/Eastern). This is a documented approximation, not an
authoritative release-time feed -- see docs/ROADMAP.md for replacing it
with the actual Fed H.15 release calendar.
"""

from datetime import UTC, datetime, time, timedelta

import httpx

from packages.common.schemas import Observation
from packages.ingestion.base import ProviderError, RateProvider
from packages.ingestion.symbol_map import get_ticker, supported_symbols

_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
_APPROX_RELEASE_TIME = time(hour=21, minute=30)  # UTC, ~16:30 US/Eastern


class FredProvider(RateProvider):
    name = "fred"

    def __init__(self, api_key: str | None, client: httpx.AsyncClient | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=15.0)

    def supports(self, symbol: str) -> bool:
        return symbol in supported_symbols(self.name)

    def _series_id(self, symbol: str) -> str:
        series_id = get_ticker(self.name, symbol)
        if series_id is None:
            raise ProviderError(self.name, f"no FRED series mapping for symbol {symbol!r}")
        return series_id

    @staticmethod
    def _available_at(observed_date: datetime) -> datetime:
        return datetime.combine(observed_date.date(), _APPROX_RELEASE_TIME, tzinfo=UTC)

    async def _fetch_observations(
        self, series_id: str, *, start: datetime | None, end: datetime | None
    ) -> list[dict]:
        if not self._api_key:
            raise ProviderError(self.name, "FRED_API_KEY is not configured")

        params: dict[str, str] = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
        }
        if start is not None:
            params["observation_start"] = start.strftime("%Y-%m-%d")
        if end is not None:
            params["observation_end"] = end.strftime("%Y-%m-%d")

        try:
            response = await self._client.get(_BASE_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(
                self.name, f"request failed for series {series_id}: {exc}", cause=exc
            ) from exc

        payload = response.json()
        observations = payload.get("observations")
        if observations is None:
            raise ProviderError(self.name, f"malformed response for series {series_id}")
        return observations

    def _to_observations(self, symbol: str, series_id: str, raw: list[dict]) -> list[Observation]:
        now = datetime.now(UTC)
        out: list[Observation] = []
        for row in raw:
            if row.get("value") in (None, ".", ""):
                continue  # FRED uses "." for missing prints
            observed_at = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=UTC)
            out.append(
                Observation(
                    source=self.name,
                    symbol=symbol,
                    observed_at=observed_at,
                    available_at=self._available_at(observed_at),
                    ingested_at=now,
                    value=float(row["value"]),
                    metadata={"series_id": series_id},
                )
            )
        return out

    async def get_history(self, symbol: str, start: datetime, end: datetime) -> list[Observation]:
        series_id = self._series_id(symbol)
        raw = await self._fetch_observations(series_id, start=start, end=end)
        return self._to_observations(symbol, series_id, raw)

    async def get_quote(self, symbol: str) -> Observation:
        series_id = self._series_id(symbol)
        end = datetime.now(UTC)
        start = end - timedelta(days=14)
        raw = await self._fetch_observations(series_id, start=start, end=end)
        observations = self._to_observations(symbol, series_id, raw)
        if not observations:
            raise ProviderError(self.name, f"no recent observations for series {series_id}")
        return observations[-1]

    async def aclose(self) -> None:
        await self._client.aclose()
