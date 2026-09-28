"""Agent 1 -- Market Data Agent (plan section 50).

Responsibilities: collect, normalize, validate, store. A thin, uniform
orchestration wrapper over packages.ingestion.pipeline -- the "collect and
store" half of the plan's split between raw ingestion and interpretation
(the latter lives in RatesMacroAgent / PositioningAgent).
"""

from datetime import datetime

from sqlalchemy.orm import Session

from packages.agents.base import AgentResult
from packages.common.config import get_settings
from packages.common.symbols import CORE_SYMBOLS
from packages.ingestion.pipeline import ingest_price_history, ingest_rate_history
from packages.ingestion.providers.fred import FredProvider
from packages.ingestion.providers.yahoo_finance import YahooFinanceProvider

_RATE_SYMBOLS = {"US02Y", "US05Y", "US10Y", "US10Y_REAL"}


async def run(session: Session, start: datetime, end: datetime) -> AgentResult:
    settings = get_settings()
    price_symbols = [s.value for s in CORE_SYMBOLS if s.value not in _RATE_SYMBOLS]
    rate_symbols = [s.value for s in CORE_SYMBOLS if s.value in _RATE_SYMBOLS]

    yahoo = YahooFinanceProvider()
    fred = FredProvider(api_key=settings.fred_api_key)
    try:
        price_results = await ingest_price_history(session, [yahoo], price_symbols, start, end)
        rate_results = await ingest_rate_history(session, [fred], rate_symbols, start, end)
    finally:
        await yahoo.aclose()
        await fred.aclose()

    total_prices = sum(price_results.values())
    total_rates = sum(rate_results.values())
    return AgentResult(
        agent="market_data",
        status="ok",
        detail=f"ingested {total_prices} price rows across {len(price_symbols)} symbols, "
        f"{total_rates} rate rows across {len(rate_symbols)} symbols",
        data={"prices": price_results, "rates": rate_results},
    )
