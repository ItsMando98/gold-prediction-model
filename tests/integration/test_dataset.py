from datetime import UTC, datetime, timedelta

from packages.backtesting.dataset import build_dataset, dataset_metadata, feature_columns
from packages.ingestion.store import persist_bars
from tests.conftest import make_bars


def test_build_dataset_shape_and_columns(db):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = [2000.0 + i * 3 for i in range(60)]
    persist_bars(db, make_bars("XAUUSD", "test", start, closes))
    db.commit()

    as_of_dates = [start + timedelta(days=d) for d in (20, 27, 34, 41, 48)]
    df = build_dataset(db, "XAUUSD", as_of_dates)

    assert len(df) == 5
    assert "xauusd_return_5d" in df.columns
    assert "label_return_5d" in df.columns
    assert list(df.index) == sorted(as_of_dates)

    cols = feature_columns(df)
    assert "label_return_5d" not in cols
    assert "symbol" not in cols
    assert "xauusd_return_5d" in cols


def test_dataset_metadata_reports_version_and_size(db):
    df = build_dataset(db, "XAUUSD", [datetime(2026, 1, 1, tzinfo=UTC)])
    meta = dataset_metadata(df)
    assert meta["n_rows"] == 1
    assert meta["feature_set_version"] == "v1"
