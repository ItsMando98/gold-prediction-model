"""Pre-fetched, point-in-time data handed to every feature definition."""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from packages.features.data_access import price_series, rate_series

PRICE_SYMBOLS: tuple[str, ...] = (
    "XAUUSD",
    "GC",
    "DXY",
    "BRENT",
    "WTI",
    "VIX",
    "SILVER",
    "COPPER",
    "SPX",
    "USDJPY",
    "EURUSD",
)

RATE_SYMBOLS: tuple[str, ...] = ("US02Y", "US05Y", "US10Y", "US10Y_REAL")


@dataclass
class FeatureContext:
    as_of: datetime
    prices: dict[str, pd.DataFrame] = field(default_factory=dict)
    rates: dict[str, pd.Series] = field(default_factory=dict)


def build_context(session: Session, as_of: datetime, lookback_days: int = 400) -> FeatureContext:
    prices = {s: price_series(session, s, as_of, lookback_days) for s in PRICE_SYMBOLS}
    rates = {s: rate_series(session, s, as_of, lookback_days) for s in RATE_SYMBOLS}
    return FeatureContext(as_of=as_of, prices=prices, rates=rates)
