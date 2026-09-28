"""Yahoo Finance chart API provider for tradable instruments (OHLCV bars).

Covers XAUUSD, GC, DXY, Brent, WTI, VIX, Silver, Copper, SPX, USDJPY, EURUSD
(plan section 3). Requires outbound HTTPS access to
``query1.finance.yahoo.com`` -- not available from every environment (e.g.
this repo's sandbox), so this module is unit-tested against mocked HTTP
responses rather than live calls.
"""

from datetime import UTC, datetime

import httpx

from packages.common.schemas import Bar
from packages.ingestion.base import PriceProvider, ProviderError
from packages.ingestion.symbol_map import get_ticker, supported_symbols

_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


class YahooFinanceProvider(PriceProvider):
    name = "yahoo_finance"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=15.0)

    def supports(self, symbol: str) -> bool:
        return symbol in supported_symbols(self.name)

    def _ticker(self, symbol: str) -> str:
        ticker = get_ticker(self.name, symbol)
        if ticker is None:
            raise ProviderError(self.name, f"no ticker mapping for symbol {symbol!r}")
        return ticker

    async def _fetch_chart(
        self, ticker: str, *, period1: int | None, period2: int | None, interval: str, range_: str | None
    ) -> dict:
        params: dict[str, str | int] = {"interval": interval}
        if range_ is not None:
            params["range"] = range_
        else:
            params["period1"] = period1
            params["period2"] = period2

        try:
            response = await self._client.get(_BASE_URL.format(ticker=ticker), params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(self.name, f"request failed for {ticker}: {exc}", cause=exc) from exc

        payload = response.json()
        result = (payload.get("chart") or {}).get("result")
        if not result:
            error = (payload.get("chart") or {}).get("error")
            raise ProviderError(self.name, f"no chart result for {ticker}: {error}")
        return result[0]

    def _bars_from_result(self, symbol: str, ticker: str, result: dict) -> list[Bar]:
        timestamps = result.get("timestamp") or []
        quote = (result.get("indicators") or {}).get("quote", [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        now = datetime.now(UTC)
        bars: list[Bar] = []
        for i, ts in enumerate(timestamps):
            o, h, low_, c = opens[i], highs[i], lows[i], closes[i]
            if o is None or h is None or low_ is None or c is None:
                continue  # exchange holiday / no trade -> Yahoo returns nulls
            observed_at = datetime.fromtimestamp(ts, tz=UTC)
            bars.append(
                Bar(
                    source=self.name,
                    symbol=symbol,
                    observed_at=observed_at,
                    available_at=observed_at,
                    ingested_at=now,
                    open=o,
                    high=h,
                    low=low_,
                    close=c,
                    volume=volumes[i] if i < len(volumes) else None,
                    metadata={"vendor_ticker": ticker},
                )
            )
        return bars

    async def get_history(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        ticker = self._ticker(symbol)
        result = await self._fetch_chart(
            ticker,
            period1=int(start.timestamp()),
            period2=int(end.timestamp()),
            interval="1d",
            range_=None,
        )
        return self._bars_from_result(symbol, ticker, result)

    async def get_quote(self, symbol: str) -> Bar:
        ticker = self._ticker(symbol)
        result = await self._fetch_chart(ticker, period1=None, period2=None, interval="1d", range_="5d")
        bars = self._bars_from_result(symbol, ticker, result)
        if not bars:
            raise ProviderError(self.name, f"no recent bars returned for {ticker}")
        return bars[-1]

    async def aclose(self) -> None:
        await self._client.aclose()
