from datetime import UTC, datetime

from sqlalchemy import select

from packages.common.db.models import MarketPrice, RateObservation
from packages.ingestion.store import persist_bars, persist_observations
from tests.conftest import make_bars, make_observations


def test_persist_bars_is_idempotent_on_reingest(db):
    start = datetime(2026, 6, 1, tzinfo=UTC)
    bars = make_bars("XAUUSD", "yahoo_finance", start, [100.0, 101.0, 102.0])

    persist_bars(db, bars)
    db.commit()
    persist_bars(db, bars)  # re-ingest same window
    db.commit()

    rows = db.execute(select(MarketPrice).where(MarketPrice.symbol == "XAUUSD")).scalars().all()
    assert len(rows) == 3


def test_persist_bars_updates_close_on_conflict(db):
    start = datetime(2026, 6, 1, tzinfo=UTC)
    bars = make_bars("XAUUSD", "yahoo_finance", start, [100.0])
    persist_bars(db, bars)
    db.commit()

    revised = make_bars("XAUUSD", "yahoo_finance", start, [105.0])
    persist_bars(db, revised)
    db.commit()

    row = db.execute(select(MarketPrice).where(MarketPrice.symbol == "XAUUSD")).scalars().one()
    assert row.close == 105.0


def test_persist_observations_is_idempotent(db):
    start = datetime(2026, 6, 1, tzinfo=UTC)
    observations = make_observations("US10Y", "fred", start, [4.0, 4.1])
    persist_observations(db, observations)
    db.commit()
    persist_observations(db, observations)
    db.commit()

    rows = db.execute(select(RateObservation).where(RateObservation.symbol == "US10Y")).scalars().all()
    assert len(rows) == 2


def test_persist_empty_list_is_a_noop(db):
    assert persist_bars(db, []) == 0
    assert persist_observations(db, []) == 0
