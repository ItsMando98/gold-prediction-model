from datetime import UTC, datetime, timedelta

import pytest

from packages.agents import regime_agent
from packages.regimes.types import Regime


@pytest.mark.asyncio
async def test_first_run_has_no_previous_regime(db):
    as_of = datetime(2026, 6, 5, tzinfo=UTC)
    features = {"real_yield_10y_change_5d_bps": 20.0, "dxy_return_5d": 0.015, "xauusd_return_5d": -0.02}

    result = await regime_agent.run(db, "XAUUSD", as_of, features)
    assert result.status == "ok"
    assert result.data["regime"] == Regime.RATES_DOMINATED_BEARISH.value
    assert result.data["previous_regime"] is None
    assert result.data["changed"] is False


@pytest.mark.asyncio
async def test_detects_regime_change_between_runs(db):
    bearish_features = {
        "real_yield_10y_change_5d_bps": 20.0,
        "dxy_return_5d": 0.015,
        "xauusd_return_5d": -0.02,
    }
    bullish_features = {
        "real_yield_10y_change_5d_bps": -20.0,
        "dxy_return_5d": -0.015,
        "xauusd_return_5d": 0.02,
    }
    week1 = datetime(2026, 6, 5, tzinfo=UTC)
    week2 = week1 + timedelta(days=7)

    await regime_agent.run(db, "XAUUSD", week1, bearish_features)
    result2 = await regime_agent.run(db, "XAUUSD", week2, bullish_features)

    assert result2.data["previous_regime"] == Regime.RATES_DOMINATED_BEARISH.value
    assert result2.data["regime"] == Regime.RATES_DOMINATED_BULLISH.value
    assert result2.data["changed"] is True


@pytest.mark.asyncio
async def test_no_change_when_regime_persists(db):
    features = {"real_yield_10y_change_5d_bps": 20.0, "dxy_return_5d": 0.015, "xauusd_return_5d": -0.02}
    week1 = datetime(2026, 6, 5, tzinfo=UTC)
    week2 = week1 + timedelta(days=7)

    await regime_agent.run(db, "XAUUSD", week1, features)
    result2 = await regime_agent.run(db, "XAUUSD", week2, features)
    assert result2.data["changed"] is False
