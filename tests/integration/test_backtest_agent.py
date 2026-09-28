from datetime import UTC, datetime, timedelta

import pytest

from packages.agents import backtest_agent
from packages.ingestion.store import persist_bars
from tests.conftest import make_bars


def _seed_prices(db, n_days=40):
    # Mixed up/down moves so the resulting labels aren't a single class
    # (a monotonic series would make every forward-return label "up").
    import random

    rng = random.Random(0)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = [2000.0]
    for _ in range(n_days - 1):
        closes.append(closes[-1] + rng.choice([-6.0, -3.0, 3.0, 6.0]))
    persist_bars(db, make_bars("XAUUSD", "test", start, closes))
    db.commit()
    return start


@pytest.mark.asyncio
async def test_evaluate_reports_unavailable_with_too_little_history(db):
    start = _seed_prices(db, n_days=40)
    dates = [start + timedelta(days=d) for d in range(20, 35)]

    result = await backtest_agent.evaluate(db, "XAUUSD", dates, "logistic_regression")
    assert result.status == "unavailable"
    assert result.data["metrics"]["folds"] == 0


@pytest.mark.asyncio
async def test_train_registers_a_candidate_model(db):
    start = _seed_prices(db, n_days=40)
    dates = [start + timedelta(days=d) for d in range(20, 35)]

    result = await backtest_agent.train(db, "XAUUSD", dates, "logistic_regression", name="smoke-test-model")
    assert result.status == "ok"
    assert result.data["model_version_id"]
