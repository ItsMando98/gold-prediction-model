from datetime import UTC, datetime, timedelta

import pytest

from packages.agents import rates_macro_agent
from packages.ingestion.store import persist_observations
from tests.conftest import make_observations


@pytest.mark.asyncio
async def test_run_reports_unavailable_without_data(db):
    result = await rates_macro_agent.run(db, datetime(2026, 6, 5, tzinfo=UTC))
    assert result.status == "unavailable"
    assert result.data["fed_expectations"] is None


@pytest.mark.asyncio
async def test_run_summarizes_rates_when_data_exists(db):
    start = datetime(2026, 5, 1, tzinfo=UTC)
    persist_observations(db, make_observations("US10Y", "test", start, [4.0 + i * 0.01 for i in range(40)]))
    persist_observations(db, make_observations("US02Y", "test", start, [4.3 + i * 0.005 for i in range(40)]))
    db.commit()

    result = await rates_macro_agent.run(db, start + timedelta(days=35))
    assert result.status == "ok"
    assert result.data["rates"]["us10y_level"] is not None
    assert result.data["rates"]["curve_slope_2s10s"] is not None
    assert result.data["fed_expectations"] is None
