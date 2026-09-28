"""Scheduled ingestion and prediction jobs (plan sections 36, 53-54, 87)."""

from datetime import UTC, datetime, timedelta

from packages.common.config import get_settings
from packages.common.db.session import get_sessionmaker
from packages.common.logging import get_logger
from packages.common.symbols import CORE_SYMBOLS
from packages.ingestion.pipeline import ingest_price_history, ingest_rate_history
from packages.ingestion.providers.fred import FredProvider
from packages.ingestion.providers.yahoo_finance import YahooFinanceProvider
from packages.snapshots.friday import generate_prediction

logger = get_logger(__name__)

_PRICE_SYMBOLS = [
    s
    for s in CORE_SYMBOLS
    if s.value not in {"US02Y", "US05Y", "US10Y", "US10Y_REAL"}
]
_RATE_SYMBOLS = ["US02Y", "US05Y", "US10Y", "US10Y_REAL"]


async def ingest_daily(lookback_days: int = 10) -> None:
    """Incremental pull of the last ``lookback_days`` for every core symbol."""
    settings = get_settings()
    end = datetime.now(UTC)
    start = end - timedelta(days=lookback_days)

    yahoo = YahooFinanceProvider()
    fred = FredProvider(api_key=settings.fred_api_key)

    session = get_sessionmaker()()
    try:
        await ingest_price_history(session, [yahoo], [s.value for s in _PRICE_SYMBOLS], start, end)
        await ingest_rate_history(session, [fred], _RATE_SYMBOLS, start, end)
    finally:
        session.close()
        await yahoo.aclose()
        await fred.aclose()


async def generate_weekly_prediction() -> None:
    session = get_sessionmaker()()
    try:
        prediction = generate_prediction(session)
        logger.info(
            "generated_prediction",
            prediction_id=prediction.id,
            regime=prediction.regime,
            risk_score=prediction.risk_score,
            bias=prediction.bias,
        )
    finally:
        session.close()
