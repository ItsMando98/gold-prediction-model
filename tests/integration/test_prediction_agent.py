from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from packages.agents import prediction_agent
from packages.ingestion.store import persist_bars, persist_observations
from packages.models.train import train_and_register
from tests.conftest import make_bars, make_observations

FRIDAY_CLOSE = datetime(2026, 6, 5, 21, 0, tzinfo=UTC)


def _seed_bearish_scenario(db):
    start = FRIDAY_CLOSE - timedelta(days=20)
    n = 21
    xau_closes = [2100.0 - i * 3 for i in range(n)]
    dxy_closes = [100.0 + i * 0.25 for i in range(n)]
    us10y = [4.00 + i * 0.02 for i in range(n)]
    real_yield = [1.80 + i * 0.03 for i in range(n)]

    persist_bars(db, make_bars("XAUUSD", "test", start, xau_closes))
    persist_bars(db, make_bars("DXY", "test", start, dxy_closes))
    persist_observations(db, make_observations("US10Y", "test", start, us10y))
    persist_observations(db, make_observations("US10Y_REAL", "test", start, real_yield))
    db.commit()


@pytest.mark.asyncio
async def test_run_without_active_model_is_deterministic_only(db):
    _seed_bearish_scenario(db)
    result, payload = await prediction_agent.run(db, as_of=FRIDAY_CLOSE)

    assert result.status == "ok"
    assert payload.ml_score is None
    assert "deterministic-only" in result.detail
    assert "ml_model_id" not in payload.model_versions


@pytest.mark.asyncio
async def test_run_with_active_model_blends_score_and_stays_consistent(db):
    _seed_bearish_scenario(db)

    # A model whose label is 95% "down" independent of the feature, so a fitted
    # logistic regression predicts a high P(down) for essentially any input while
    # still having seen both classes during training (a single-class label column
    # makes sklearn's fit raise).
    rng = np.random.default_rng(0)
    n = 2200
    dates = pd.date_range("2015-01-01", periods=n, freq="D")
    labels = np.where(rng.uniform(0, 1, n) < 0.95, 1.0, 0.0)
    df = pd.DataFrame(
        {"real_yield_10y_change_5d_bps": rng.normal(0, 1, n), "label_down_5d": labels}, index=dates
    )
    df.index.name = "as_of"
    version = train_and_register(db, df, "logistic_regression", name="always-down")
    version.status = "active"
    db.commit()

    result, payload = await prediction_agent.run(db, as_of=FRIDAY_CLOSE)

    assert payload.ml_score is not None
    assert payload.ml_score > 0.5  # always-down model
    assert payload.model_versions["ml_model_id"] == version.id
    assert payload.confirmations and payload.invalidation
    assert "ensemble" in result.detail
