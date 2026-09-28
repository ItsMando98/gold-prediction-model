from datetime import UTC, datetime, timedelta

from packages.features.engine import generate_snapshot
from packages.ingestion.store import persist_bars, persist_observations
from tests.conftest import make_bars, make_observations


def _seed_market_data(db, as_of: datetime) -> None:
    start = as_of - timedelta(days=30)
    xau_closes = [2000.0 + i * 2 for i in range(31)]
    dxy_closes = [100.0 + i * 0.1 for i in range(31)]
    rate_values = [4.0 + i * 0.01 for i in range(31)]

    persist_bars(db, make_bars("XAUUSD", "test", start, xau_closes))
    persist_bars(db, make_bars("DXY", "test", start, dxy_closes))
    persist_observations(db, make_observations("US10Y", "test", start, rate_values))
    persist_observations(db, make_observations("US02Y", "test", start, [v - 1 for v in rate_values]))
    persist_observations(db, make_observations("US10Y_REAL", "test", start, [v - 2 for v in rate_values]))
    db.commit()


def test_generate_snapshot_computes_expected_features(db):
    as_of = datetime(2026, 6, 5, 21, 0, tzinfo=UTC)
    _seed_market_data(db, as_of)

    snapshot = generate_snapshot(db, "XAUUSD", as_of)

    assert snapshot.symbol == "XAUUSD"
    assert snapshot.feature_set_version == "v1"
    # gold and DXY were both monotonically rising in the fixture
    assert snapshot.features["xauusd_return_5d"] > 0
    assert snapshot.features["dxy_momentum_5d"] > 0
    assert snapshot.features["us10y_change_5d_bps"] > 0
    assert snapshot.features["curve_slope_2s10s"] is not None


def test_generate_snapshot_is_idempotent_upsert(db):
    as_of = datetime(2026, 6, 5, 21, 0, tzinfo=UTC)
    _seed_market_data(db, as_of)

    first = generate_snapshot(db, "XAUUSD", as_of)
    second = generate_snapshot(db, "XAUUSD", as_of)

    assert first.id == second.id


def test_generate_snapshot_handles_missing_symbols_gracefully(db):
    as_of = datetime(2026, 6, 5, 21, 0, tzinfo=UTC)
    # No data seeded at all.
    snapshot = generate_snapshot(db, "XAUUSD", as_of)
    assert snapshot.features["xauusd_return_5d"] is None
