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

from packages.common.db.models import MarketPrice, RateObservation


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
