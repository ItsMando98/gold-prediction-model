"""Historical backfill CLI.

Usage:
    python -m apps.worker.backfill --start 2015-01-01 --end 2026-09-28

Requires network access to query1.finance.yahoo.com and (for rates)
api.stlouisfed.org with FRED_API_KEY set -- see README.md.
"""

import argparse
import asyncio
from datetime import UTC, datetime

from packages.common.config import get_settings
from packages.common.db.session import get_sessionmaker
from packages.common.logging import configure_logging, get_logger
from packages.common.symbols import CORE_SYMBOLS
from packages.ingestion.pipeline import ingest_price_history, ingest_rate_history
from packages.ingestion.providers.fred import FredProvider
from packages.ingestion.providers.yahoo_finance import YahooFinanceProvider

logger = get_logger(__name__)

_RATE_SYMBOLS = {"US02Y", "US05Y", "US10Y", "US10Y_REAL"}


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)


async def run(start: datetime, end: datetime) -> None:
    settings = get_settings()
    price_symbols = [s.value for s in CORE_SYMBOLS if s.value not in _RATE_SYMBOLS]
    rate_symbols = [s.value for s in CORE_SYMBOLS if s.value in _RATE_SYMBOLS]

    yahoo = YahooFinanceProvider()
    fred = FredProvider(api_key=settings.fred_api_key)

    session = get_sessionmaker()()
    try:
        price_results = await ingest_price_history(session, [yahoo], price_symbols, start, end)
        rate_results = await ingest_rate_history(session, [fred], rate_symbols, start, end)
        logger.info("backfill_complete", prices=price_results, rates=rate_results)
    finally:
        session.close()
        await yahoo.aclose()
        await fred.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=_parse_date, required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--end", type=_parse_date, default=datetime.now(UTC), help="YYYY-MM-DD (default: now)"
    )
    args = parser.parse_args()

    configure_logging("INFO")
    asyncio.run(run(args.start, args.end))


if __name__ == "__main__":
    main()
