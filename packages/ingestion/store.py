"""Persists Bars/Observations to the raw data store, idempotently.

Re-ingesting the same (source, symbol, observed_at, revision) is a no-op
update rather than a duplicate insert -- ingestion jobs are safe to retry
or re-run for backfills.
"""

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from packages.common.db.models import CotPosition, MarketPrice, NewsArticle, NewsEventRecord, RateObservation
from packages.common.schemas import Bar, CotRecord, NewsEvent, Observation
from packages.news.dedup import dedup_hash
from packages.news.source_tiers import cap_confidence_for_tier, tier_for_source


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


def persist_cot_records(session: Session, records: list[CotRecord]) -> int:
    if not records:
        return 0
    rows = [
        {
            "source": r.source,
            "symbol": r.symbol,
            "observed_at": r.observed_at,
            "available_at": r.available_at,
            "ingested_at": r.ingested_at,
            "revision": r.revision,
            "open_interest": r.open_interest,
            "managed_money_long": r.managed_money_long,
            "managed_money_short": r.managed_money_short,
            "producer_long": r.producer_long,
            "producer_short": r.producer_short,
            "swap_dealer_long": r.swap_dealer_long,
            "swap_dealer_short": r.swap_dealer_short,
            "other_reportable_long": r.other_reportable_long,
            "other_reportable_short": r.other_reportable_short,
            "extra": r.metadata,
        }
        for r in records
    ]
    stmt = pg_insert(CotPosition).values(rows)
    update_cols = (
        "open_interest",
        "managed_money_long",
        "managed_money_short",
        "producer_long",
        "producer_short",
        "swap_dealer_long",
        "swap_dealer_short",
        "other_reportable_long",
        "other_reportable_short",
        "available_at",
        "ingested_at",
        "extra",
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_cot_position",
        set_={col: getattr(stmt.excluded, col) for col in update_cols},
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


def persist_news_article(
    session: Session, *, source: str, headline: str, body: str | None, url: str | None, published_at: datetime
) -> NewsArticle:
    """Insert a raw article verbatim (plan section 34), deduplicating by headline+date.

    Returns the existing article on a duplicate rather than inserting a second row --
    the News Event Agent should not re-classify the same story twice.
    """
    h = dedup_hash(headline, published_at)
    stmt = (
        pg_insert(NewsArticle)
        .values(
            source=source,
            source_tier=tier_for_source(source),
            headline=headline,
            body=body,
            url=url,
            published_at=published_at,
            received_at=datetime.now(UTC),
            dedup_hash=h,
        )
        .on_conflict_do_nothing(index_elements=["dedup_hash"])
        .returning(NewsArticle.id)
    )
    inserted_id = session.execute(stmt).scalar_one_or_none()
    article_id = inserted_id or session.query(NewsArticle.id).filter_by(dedup_hash=h).scalar()
    return session.get(NewsArticle, article_id)


def persist_news_event(
    session: Session, *, article: NewsArticle, event: NewsEvent, model: str
) -> NewsEventRecord:
    """Store a News Event Agent classification, with its confidence capped to the
    source article's credibility tier (plan section 19) regardless of what the
    model itself reported."""
    record = NewsEventRecord(
        article_id=article.id,
        event=event.event,
        category=event.category.value,
        entities=event.entities,
        direct_assets=event.direct_assets,
        transmission_chain=event.transmission_chain,
        relevance=event.relevance,
        confidence=cap_confidence_for_tier(event.confidence, article.source_tier),
        rationale=event.rationale,
        model=model,
        created_at=datetime.now(UTC),
    )
    session.add(record)
    session.flush()
    return record
