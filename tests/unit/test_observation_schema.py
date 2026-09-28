from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from packages.common.schemas import Bar, Observation


def _times(offset_available=0, offset_ingested=0):
    observed_at = datetime(2026, 1, 2, tzinfo=UTC)
    available_at = observed_at + timedelta(hours=offset_available)
    ingested_at = available_at + timedelta(hours=offset_ingested)
    return observed_at, available_at, ingested_at


def test_observation_accepts_valid_ordering():
    observed_at, available_at, ingested_at = _times(1, 1)
    obs = Observation(
        source="test",
        symbol="US10Y",
        observed_at=observed_at,
        available_at=available_at,
        ingested_at=ingested_at,
        value=4.25,
    )
    assert obs.value == 4.25


def test_observation_rejects_available_before_observed():
    observed_at, _, _ = _times()
    with pytest.raises(ValidationError):
        Observation(
            source="test",
            symbol="US10Y",
            observed_at=observed_at,
            available_at=observed_at - timedelta(hours=1),
            ingested_at=observed_at,
            value=4.25,
        )


def test_observation_rejects_ingested_before_available():
    observed_at, available_at, _ = _times(1)
    with pytest.raises(ValidationError):
        Observation(
            source="test",
            symbol="US10Y",
            observed_at=observed_at,
            available_at=available_at,
            ingested_at=available_at - timedelta(minutes=1),
            value=4.25,
        )


def test_bar_shares_the_same_ordering_rule():
    observed_at, _, _ = _times()
    with pytest.raises(ValidationError):
        Bar(
            source="test",
            symbol="XAUUSD",
            observed_at=observed_at,
            available_at=observed_at - timedelta(hours=1),
            ingested_at=observed_at,
            open=1.0,
            high=1.0,
            low=1.0,
            close=1.0,
        )
