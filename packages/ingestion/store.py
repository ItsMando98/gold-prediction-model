"""Persists Bars/Observations to the raw data store, idempotently.

Re-ingesting the same (source, symbol, observed_at, revision) is a no-op
update rather than a duplicate insert -- ingestion jobs are safe to retry
or re-run for backfills.
"""

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from packages.common.db.models import MarketPrice, RateObservation
from packages.common.schemas import Bar, Observation


def persist_bars(session: Session, bars: list[Bar]) -> int:
    if not bars:
        return 0
    rows = [
        {
            "source": b.source,
            "symbol": b.symbol,
            "observed_at": b.observed_at,
            "available_at": b.available_at,
            "ingested_at": b.ingested_at,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
            "revision": b.revision,
            "extra": b.metadata,
        }
        for b in bars
    ]
    stmt = pg_insert(MarketPrice).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_market_price",
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "available_at": stmt.excluded.available_at,
            "ingested_at": stmt.excluded.ingested_at,
            "extra": stmt.excluded.extra,
        },
    )
    session.execute(stmt)
    return len(rows)


def persist_observations(session: Session, observations: list[Observation]) -> int:
    if not observations:
        return 0
    rows = [
        {
            "source": o.source,
            "symbol": o.symbol,
            "observed_at": o.observed_at,
            "available_at": o.available_at,
            "ingested_at": o.ingested_at,
            "value": o.value,
            "revision": o.revision,
            "extra": o.metadata,
        }
        for o in observations
    ]
    stmt = pg_insert(RateObservation).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_rate_obs",
        set_={
            "value": stmt.excluded.value,
            "available_at": stmt.excluded.available_at,
            "ingested_at": stmt.excluded.ingested_at,
            "extra": stmt.excluded.extra,
        },
    )
    session.execute(stmt)
    return len(rows)
