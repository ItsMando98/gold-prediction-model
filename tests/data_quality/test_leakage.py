"""Point-in-time / leakage protection tests (plan section 33).

These assert the core invariant the whole backtest depends on:
``feature_timestamp`` reads must never see an observation whose
``available_at`` is later than the query's ``as_of``.
"""

from datetime import UTC, datetime, timedelta

from packages.features.data_access import price_series, rate_series
from packages.ingestion.store import persist_bars, persist_observations
from tests.conftest import make_bars, make_observations


def test_price_series_excludes_data_not_yet_available(db):
    as_of = datetime(2026, 6, 5, 21, 0, tzinfo=UTC)
    bars = make_bars("XAUUSD", "test", as_of - timedelta(days=3), [100.0, 101.0, 102.0])
    # Simulate a late-arriving/revised bar that becomes available *after* as_of.
    from packages.common.schemas import Bar

    future_bar = Bar(
        source="test",
        symbol="XAUUSD",
        observed_at=as_of - timedelta(days=1),
        available_at=as_of + timedelta(days=1),  # only known AFTER as_of
        ingested_at=as_of + timedelta(days=1),
        revision=1,  # a later revision of the same observed_at bar
        open=999.0,
        high=999.0,
        low=999.0,
        close=999.0,
    )
    persist_bars(db, bars + [future_bar])
    db.commit()

    series = price_series(db, "XAUUSD", as_of)
    assert 999.0 not in series["close"].values


def test_rate_series_excludes_data_not_yet_available(db):
    as_of = datetime(2026, 6, 5, 21, 0, tzinfo=UTC)
    observations = make_observations("US10Y", "test", as_of - timedelta(days=3), [4.0, 4.1, 4.2])
    from packages.common.schemas import Observation

    future_obs = Observation(
        source="test",
        symbol="US10Y",
        observed_at=as_of - timedelta(days=1),
        available_at=as_of + timedelta(hours=1),
        ingested_at=as_of + timedelta(hours=1),
        revision=1,  # a later revision of the same observed_at print
        value=99.0,
    )
    persist_observations(db, observations + [future_obs])
    db.commit()

    series = rate_series(db, "US10Y", as_of)
    assert 99.0 not in series.values


def test_revision_resolves_to_latest_known_at_as_of(db):
    """A later revision only counts once its available_at has passed."""
    as_of_early = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    as_of_late = datetime(2026, 6, 5, 23, 0, tzinfo=UTC)
    observed_at = datetime(2026, 6, 5, 0, 0, tzinfo=UTC)

    from packages.common.schemas import Observation

    first_print = Observation(
        source="test",
        symbol="US10Y",
        observed_at=observed_at,
        available_at=datetime(2026, 6, 5, 9, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 6, 5, 9, 0, tzinfo=UTC),
        value=4.00,
        revision=0,
    )
    revised_print = Observation(
        source="test",
        symbol="US10Y",
        observed_at=observed_at,
        available_at=datetime(2026, 6, 5, 18, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 6, 5, 18, 0, tzinfo=UTC),
        value=4.10,
        revision=1,
    )
    persist_observations(db, [first_print, revised_print])
    db.commit()

    early_series = rate_series(db, "US10Y", as_of_early)
    late_series = rate_series(db, "US10Y", as_of_late)

    assert early_series.iloc[-1] == 4.00
    assert late_series.iloc[-1] == 4.10
