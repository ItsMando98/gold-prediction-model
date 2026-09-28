"""Ingestion orchestration with provider failover (plan section 80).

For each symbol, providers are tried in order; the first one that both
supports the symbol and returns data wins. Every attempt (success or
failure) is recorded in provider_health so data-quality dashboards can see
which feeds are flaky.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from packages.common.logging import get_logger
from packages.ingestion.base import PositioningProvider, PriceProvider, ProviderError, RateProvider
from packages.ingestion.health import record_health
from packages.ingestion.store import persist_bars, persist_cot_records, persist_observations

logger = get_logger(__name__)


async def ingest_price_history(
    session: Session,
    providers: list[PriceProvider],
    symbols: list[str],
    start: datetime,
    end: datetime,
) -> dict[str, int]:
    """Backfill OHLCV history for each symbol via the first supporting provider."""
    results: dict[str, int] = {}
    for symbol in symbols:
        results[symbol] = 0
        for provider in providers:
            if not provider.supports(symbol):
                continue
            t0 = datetime.now()
            try:
                bars = await provider.get_history(symbol, start, end)
                latency_ms = (datetime.now() - t0).total_seconds() * 1000
                record_health(
                    session, source=provider.name, symbol=symbol, status="ok", latency_ms=latency_ms
                )
                count = persist_bars(session, bars)
                results[symbol] = count
                logger.info("ingested_price_history", symbol=symbol, provider=provider.name, count=count)
                break
            except ProviderError as exc:
                latency_ms = (datetime.now() - t0).total_seconds() * 1000
                record_health(
                    session,
                    source=provider.name,
                    symbol=symbol,
                    status="down",
                    latency_ms=latency_ms,
                    message=str(exc),
                )
                logger.warning("price_provider_failed", symbol=symbol, provider=provider.name, error=str(exc))
        else:
            logger.error("no_price_provider_supported_symbol", symbol=symbol)
        session.commit()
    return results


async def ingest_rate_history(
    session: Session,
    providers: list[RateProvider],
    symbols: list[str],
    start: datetime,
    end: datetime,
) -> dict[str, int]:
    """Backfill scalar history for each symbol via the first supporting provider."""
    results: dict[str, int] = {}
    for symbol in symbols:
        results[symbol] = 0
        for provider in providers:
            if not provider.supports(symbol):
                continue
            t0 = datetime.now()
            try:
                observations = await provider.get_history(symbol, start, end)
                latency_ms = (datetime.now() - t0).total_seconds() * 1000
                record_health(
                    session, source=provider.name, symbol=symbol, status="ok", latency_ms=latency_ms
                )
                count = persist_observations(session, observations)
                results[symbol] = count
                logger.info("ingested_rate_history", symbol=symbol, provider=provider.name, count=count)
                break
            except ProviderError as exc:
                latency_ms = (datetime.now() - t0).total_seconds() * 1000
                record_health(
                    session,
                    source=provider.name,
                    symbol=symbol,
                    status="down",
                    latency_ms=latency_ms,
                    message=str(exc),
                )
                logger.warning("rate_provider_failed", symbol=symbol, provider=provider.name, error=str(exc))
        else:
            logger.error("no_rate_provider_supported_symbol", symbol=symbol)
        session.commit()
    return results


async def ingest_positioning_history(
    session: Session,
    providers: list[PositioningProvider],
    symbols: list[str],
    start: datetime,
    end: datetime,
) -> dict[str, int]:
    """Backfill weekly COT history for each symbol via the first supporting provider."""
    results: dict[str, int] = {}
    for symbol in symbols:
        results[symbol] = 0
        for provider in providers:
            if not provider.supports(symbol):
                continue
            t0 = datetime.now()
            try:
                records = await provider.get_history(symbol, start, end)
                latency_ms = (datetime.now() - t0).total_seconds() * 1000
                record_health(
                    session, source=provider.name, symbol=symbol, status="ok", latency_ms=latency_ms
                )
                count = persist_cot_records(session, records)
                results[symbol] = count
                logger.info(
                    "ingested_positioning_history", symbol=symbol, provider=provider.name, count=count
                )
                break
            except ProviderError as exc:
                latency_ms = (datetime.now() - t0).total_seconds() * 1000
                record_health(
                    session,
                    source=provider.name,
                    symbol=symbol,
                    status="down",
                    latency_ms=latency_ms,
                    message=str(exc),
                )
                logger.warning(
                    "positioning_provider_failed", symbol=symbol, provider=provider.name, error=str(exc)
                )
        else:
            logger.error("no_positioning_provider_supported_symbol", symbol=symbol)
        session.commit()
    return results
