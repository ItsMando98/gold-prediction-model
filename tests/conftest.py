import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from packages.common.db import models  # noqa: F401  -- registers tables on Base.metadata
from packages.common.db.base import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://gold:gold@localhost:5432/gold_prediction_test"
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine) -> Iterator[Session]:
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())


@pytest.fixture
def base_time() -> datetime:
    return datetime(2026, 6, 5, 21, 0, tzinfo=UTC)  # a Friday close


def make_bars(symbol: str, source: str, start: datetime, closes: list[float]) -> list:
    from packages.common.schemas import Bar

    bars = []
    for i, close in enumerate(closes):
        observed_at = start + timedelta(days=i)
        bars.append(
            Bar(
                source=source,
                symbol=symbol,
                observed_at=observed_at,
                available_at=observed_at,
                ingested_at=observed_at,
                open=close,
                high=close * 1.002,
                low=close * 0.998,
                close=close,
                volume=1000.0,
            )
        )
    return bars


def make_observations(symbol: str, source: str, start: datetime, values: list[float]) -> list:
    from packages.common.schemas import Observation

    observations = []
    for i, value in enumerate(values):
        observed_at = start + timedelta(days=i)
        observations.append(
            Observation(
                source=source,
                symbol=symbol,
                observed_at=observed_at,
                available_at=observed_at,
                ingested_at=observed_at,
                value=value,
            )
        )
    return observations
