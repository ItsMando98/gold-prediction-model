"""Scheduled ingestion and prediction jobs (plan sections 36, 53-54, 87)."""

from datetime import UTC, datetime, timedelta

from packages.agents import positioning_agent
from packages.agents.orchestrator import run_weekly_pipeline
from packages.common.config import get_settings
from packages.common.db.session import get_sessionmaker
from packages.common.logging import get_logger
from packages.common.symbols import CORE_SYMBOLS
from packages.ingestion.pipeline import ingest_price_history, ingest_rate_history
from packages.ingestion.providers.fred import FredProvider
from packages.ingestion.providers.yahoo_finance import YahooFinanceProvider

logger = get_logger(__name__)

_RATE_SYMBOLS_SET = {"US02Y", "US05Y", "US10Y", "US10Y_REAL"}
_PRICE_SYMBOLS = [s for s in CORE_SYMBOLS if s.value not in _RATE_SYMBOLS_SET]
_RATE_SYMBOLS = ["US02Y", "US05Y", "US10Y", "US10Y_REAL"]


async def ingest_daily(lookback_days: int = 10) -> None:
    """Incremental pull of the last ``lookback_days`` for every core symbol,
    plus weekly CFTC positioning (idempotent to run daily -- the provider
    only ever has new rows on the Friday they're published)."""
    settings = get_settings()
    end = datetime.now(UTC)
    start = end - timedelta(days=lookback_days)

    yahoo = YahooFinanceProvider()
    fred = FredProvider(api_key=settings.fred_api_key)

    session = get_sessionmaker()()
    try:
        await ingest_price_history(session, [yahoo], [s.value for s in _PRICE_SYMBOLS], start, end)
        await ingest_rate_history(session, [fred], _RATE_SYMBOLS, start, end)
        await positioning_agent.ingest(session, start, end)
    finally:
        session.close()
        await yahoo.aclose()
        await fred.aclose()


async def generate_weekly_prediction() -> None:
    """Runs the full Agent Team pipeline (plan section 50) for the Friday close.

    ``generate_narrative`` is best-effort: without ``ANTHROPIC_API_KEY``
    configured, the prediction still persists with ``narrative=None`` -- see
    packages/agents/orchestrator.py. No live news feed is connected yet
    (docs/ROADMAP.md), so this run never has ``news_articles`` to classify.
    """
    session = get_sessionmaker()()
    try:
        report = await run_weekly_pipeline(session, ingest_market_data=False, generate_narrative=True)
        prediction = report.prediction
        logger.info(
            "generated_prediction",
            prediction_id=prediction.id,
            regime=prediction.regime,
            risk_score=prediction.risk_score,
            bias=prediction.bias,
            has_narrative=prediction.narrative is not None,
            agent_statuses={r.agent: r.status for r in report.agent_results},
        )
    finally:
        session.close()
