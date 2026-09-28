"""Pre-fetched, point-in-time data handed to every feature definition."""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from packages.features.data_access import cot_series, price_series, rate_series, recent_news_events

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

# COT is only reported for the futures contract, not the spot/cash pair.
COT_SYMBOLS: tuple[str, ...] = ("GC",)


@dataclass
class FeatureContext:
    as_of: datetime
    prices: dict[str, pd.DataFrame] = field(default_factory=dict)
    rates: dict[str, pd.Series] = field(default_factory=dict)
    cot: dict[str, pd.DataFrame] = field(default_factory=dict)
    news: list[dict] = field(default_factory=list)


def build_context(session: Session, as_of: datetime, lookback_days: int = 400) -> FeatureContext:
    prices = {s: price_series(session, s, as_of, lookback_days) for s in PRICE_SYMBOLS}
    rates = {s: rate_series(session, s, as_of, lookback_days) for s in RATE_SYMBOLS}
    cot = {s: cot_series(session, s, as_of, lookback_days=1200) for s in COT_SYMBOLS}
    news = recent_news_events(session, as_of)
    return FeatureContext(as_of=as_of, prices=prices, rates=rates, cot=cot, news=news)
