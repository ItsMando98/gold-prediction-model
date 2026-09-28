from datetime import UTC, datetime, timedelta

import pytest

from packages.backtesting.labels import compute_labels
from packages.ingestion.store import persist_bars
from tests.conftest import make_bars


def test_labels_computed_from_future_prices(db):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = [100.0 + i for i in range(20)]  # monotonically rising 1/day
    persist_bars(db, make_bars("XAUUSD", "test", start, closes))
    db.commit()

    as_of = start + timedelta(days=10)  # close = 110.0
    labels = compute_labels(db, "XAUUSD", as_of)

    assert labels["label_return_1d"] == pytest.approx(111.0 / 110.0 - 1.0)
    assert labels["label_down_1d"] == 0.0
    assert labels["label_return_5d"] == pytest.approx(115.0 / 110.0 - 1.0)
    assert labels["label_down_5d"] == 0.0
    assert labels["label_up_gt_1pct_5d"] == 1.0
    assert labels["label_down_gt_1pct_5d"] == 0.0


def test_labels_down_move(db):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = [130.0 - i for i in range(20)]  # falling
    persist_bars(db, make_bars("XAUUSD", "test", start, closes))
    db.commit()

    as_of = start + timedelta(days=10)
    labels = compute_labels(db, "XAUUSD", as_of)

    assert labels["label_down_1d"] == 1.0
    assert labels["label_down_5d"] == 1.0
    assert labels["label_down_gt_1pct_5d"] == 1.0
    assert labels["label_up_gt_1pct_5d"] == 0.0


def test_labels_missing_future_data_returns_none(db):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = [100.0, 101.0, 102.0]
    persist_bars(db, make_bars("XAUUSD", "test", start, closes))
    db.commit()

    as_of = start + timedelta(days=2)  # last bar -- no future data at all
    labels = compute_labels(db, "XAUUSD", as_of)
    assert labels["label_return_1d"] is None
    assert labels["label_return_5d"] is None


def test_labels_no_history_returns_all_none(db):
    labels = compute_labels(db, "XAUUSD", datetime(2026, 1, 1, tzinfo=UTC))
    assert all(v is None for v in labels.values())
