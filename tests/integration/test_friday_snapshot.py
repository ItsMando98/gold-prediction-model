from datetime import UTC, datetime, timedelta

from packages.common.db.models import Prediction
from packages.ingestion.store import persist_bars, persist_observations
from packages.regimes.types import Regime
from packages.snapshots.friday import generate_prediction, most_recent_friday_close
from tests.conftest import make_bars, make_observations

FRIDAY_CLOSE = datetime(2026, 6, 5, 21, 0, tzinfo=UTC)  # a real Friday


def test_most_recent_friday_close_on_a_friday_returns_same_day():
    reference = datetime(2026, 6, 5, 22, 0, tzinfo=UTC)
    assert most_recent_friday_close(reference) == FRIDAY_CLOSE


def test_most_recent_friday_close_before_close_rolls_back_a_week():
    reference = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)  # Friday, before close
    assert most_recent_friday_close(reference) == FRIDAY_CLOSE - timedelta(days=7)


def test_most_recent_friday_close_on_a_sunday():
    reference = datetime(2026, 6, 7, 12, 0, tzinfo=UTC)
    assert most_recent_friday_close(reference) == FRIDAY_CLOSE


def _seed_rates_dominated_bearish_scenario(db) -> None:
    start = FRIDAY_CLOSE - timedelta(days=20)
    n = 21
    # Gold sells off, DXY and yields rise steadily into Friday's close.
    xau_closes = [2100.0 - i * 3 for i in range(n)]
    dxy_closes = [100.0 + i * 0.25 for i in range(n)]
    us10y = [4.00 + i * 0.02 for i in range(n)]
    real_yield = [1.80 + i * 0.03 for i in range(n)]
    us02y = [4.30 + i * 0.005 for i in range(n)]

    persist_bars(db, make_bars("XAUUSD", "test", start, xau_closes))
    persist_bars(db, make_bars("DXY", "test", start, dxy_closes))
    persist_observations(db, make_observations("US10Y", "test", start, us10y))
    persist_observations(db, make_observations("US10Y_REAL", "test", start, real_yield))
    persist_observations(db, make_observations("US02Y", "test", start, us02y))
    db.commit()


def test_generate_prediction_end_to_end_bearish_scenario(db):
    _seed_rates_dominated_bearish_scenario(db)

    prediction = generate_prediction(db, as_of=FRIDAY_CLOSE)

    assert prediction.regime == Regime.RATES_DOMINATED_BEARISH.value
    assert prediction.bias == "bearish"
    assert prediction.risk_score > 50.0
    assert prediction.target_time == FRIDAY_CLOSE + timedelta(days=3)
    assert prediction.horizon == "weekend_to_monday_close"
    assert prediction.confirmations
    assert prediction.invalidation
    assert prediction.key_levels["support"]
    assert prediction.model_versions["calibrated"] is False
    assert len(prediction.drivers) == 8  # one per weighted component


def test_prediction_is_immutable_each_call_creates_a_new_row(db):
    _seed_rates_dominated_bearish_scenario(db)

    first = generate_prediction(db, as_of=FRIDAY_CLOSE)
    second = generate_prediction(db, as_of=FRIDAY_CLOSE)

    assert first.id != second.id
    count = db.query(Prediction).count()
    assert count == 2
