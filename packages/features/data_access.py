"""Point-in-time-correct readers for market_prices / rates.

Every query here filters on ``available_at <= as_of`` -- never on
``observed_at`` alone -- and, for series that get revised, resolves each
observation date to the most recent revision that was actually knowable
at ``as_of``. This is the enforcement point for plan section 33 (leakage
protection): a feature or backtest that reads through this module cannot
see data it wasn't allowed to see yet.
"""

from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.common.db.models import CotPosition, MarketPrice, NewsEventRecord, RateObservation

_COT_VALUE_COLUMNS = [
    "open_interest",
    "managed_money_long",
    "managed_money_short",
    "producer_long",
    "producer_short",
    "swap_dealer_long",
    "swap_dealer_short",
    "other_reportable_long",
    "other_reportable_short",
]


def _resolve_point_in_time(df: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    """Collapse multiple revisions per observed_at to the latest known-at-as_of one."""
    if df.empty:
        return df
    df = df.sort_values(["observed_at", "available_at"])
    df = df.groupby("observed_at", as_index=True).last()
    return df[value_cols]


def price_series(
    session: Session, symbol: str, as_of: datetime, lookback_days: int = 400
) -> pd.DataFrame:
    """OHLCV history for ``symbol`` up to and including ``as_of``, point-in-time correct."""
    start = as_of - timedelta(days=lookback_days)
    stmt = (
        select(MarketPrice)
        .where(MarketPrice.symbol == symbol)
        .where(MarketPrice.available_at <= as_of)
        .where(MarketPrice.observed_at >= start)
        .where(MarketPrice.observed_at <= as_of)
        .order_by(MarketPrice.observed_at.asc(), MarketPrice.available_at.asc())
    )
    rows = session.execute(stmt).scalars().all()
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame(
        [
            {
                "observed_at": r.observed_at,
                "available_at": r.available_at,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]
    )
    return _resolve_point_in_time(df, ["open", "high", "low", "close", "volume"])


def rate_series(
    session: Session, symbol: str, as_of: datetime, lookback_days: int = 400
) -> pd.Series:
    """Scalar value history for ``symbol`` up to and including ``as_of``, point-in-time correct."""
    start = as_of - timedelta(days=lookback_days)
    stmt = (
        select(RateObservation)
        .where(RateObservation.symbol == symbol)
        .where(RateObservation.available_at <= as_of)
        .where(RateObservation.observed_at >= start)
        .where(RateObservation.observed_at <= as_of)
        .order_by(RateObservation.observed_at.asc(), RateObservation.available_at.asc())
    )
    rows = session.execute(stmt).scalars().all()
    if not rows:
        return pd.Series(dtype=float)

    df = pd.DataFrame(
        [
            {"observed_at": r.observed_at, "available_at": r.available_at, "value": r.value}
            for r in rows
        ]
    )
    resolved = _resolve_point_in_time(df, ["value"])
    return resolved["value"]


def full_price_history(session: Session, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    """OHLCV history **not** gated by ``available_at`` -- returns the latest known
    revision for each ``observed_at`` in range, regardless of when it became
    available.

    This exists for exactly one legitimate use: computing backtest labels,
    where looking forward from an ``as_of`` is the point (plan section 23).
    Using this function inside a feature definition is a leakage bug --
    features must go through ``price_series`` above.
    """
    stmt = (
        select(MarketPrice)
        .where(MarketPrice.symbol == symbol)
        .where(MarketPrice.observed_at >= start)
        .where(MarketPrice.observed_at <= end)
        .order_by(MarketPrice.observed_at.asc(), MarketPrice.available_at.asc())
    )
    rows = session.execute(stmt).scalars().all()
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame(
        [
            {
                "observed_at": r.observed_at,
                "available_at": r.available_at,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]
    )
    return _resolve_point_in_time(df, ["open", "high", "low", "close", "volume"])


def cot_series(
    session: Session, symbol: str, as_of: datetime, lookback_days: int = 900
) -> pd.DataFrame:
    """Weekly COT positioning history for ``symbol`` up to ``as_of``, point-in-time
    correct. Default lookback is ~2.5 years to support 1y z-score features."""
    start = as_of - timedelta(days=lookback_days)
    stmt = (
        select(CotPosition)
        .where(CotPosition.symbol == symbol)
        .where(CotPosition.available_at <= as_of)
        .where(CotPosition.observed_at >= start)
        .where(CotPosition.observed_at <= as_of)
        .order_by(CotPosition.observed_at.asc(), CotPosition.available_at.asc())
    )
    rows = session.execute(stmt).scalars().all()
    if not rows:
        return pd.DataFrame(columns=_COT_VALUE_COLUMNS)

    df = pd.DataFrame(
        [
            {
                "observed_at": r.observed_at,
                "available_at": r.available_at,
                **{col: getattr(r, col) for col in _COT_VALUE_COLUMNS},
            }
            for r in rows
        ]
    )
    return _resolve_point_in_time(df, _COT_VALUE_COLUMNS)


def recent_news_events(session: Session, as_of: datetime, lookback_days: int = 5) -> list[dict]:
    """News events whose source article was published in ``[as_of - lookback, as_of]``.

    Point-in-time gate: an event can never be knowable before the article
    it was extracted from was published, so this joins on
    ``NewsArticle.published_at``, not ``NewsEventRecord.created_at``
    (extraction can happen well after publication on a backfill).
    """
    from packages.common.db.models import NewsArticle  # local import avoids a cycle at module load

    start = as_of - timedelta(days=lookback_days)
    stmt = (
        select(NewsEventRecord, NewsArticle.published_at, NewsArticle.source_tier)
        .join(NewsArticle, NewsEventRecord.article_id == NewsArticle.id)
        .where(NewsArticle.published_at <= as_of)
        .where(NewsArticle.published_at >= start)
        .order_by(NewsArticle.published_at.asc())
    )
    rows = session.execute(stmt).all()
    return [
        {
            "event": event.event,
            "category": event.category,
            "transmission_chain": event.transmission_chain,
            "confidence": event.confidence,
            "relevance": event.relevance,
            "source_tier": source_tier,
            "published_at": published_at,
        }
        for event, published_at, source_tier in rows
    ]
