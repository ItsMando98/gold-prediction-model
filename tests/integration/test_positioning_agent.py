from datetime import UTC, datetime, timedelta

import pytest

from packages.agents import positioning_agent
from packages.ingestion.store import persist_cot_records


def _cot_records(n=60):
    from packages.common.schemas import CotRecord

    start = datetime(2025, 1, 7, tzinfo=UTC)  # a Tuesday
    records = []
    for i in range(n):
        observed_at = start + timedelta(weeks=i)
        records.append(
            CotRecord(
                source="test",
                symbol="GC",
                observed_at=observed_at,
                available_at=observed_at + timedelta(days=3),
                ingested_at=observed_at + timedelta(days=3),
                open_interest=450_000.0,
                managed_money_long=150_000.0 + i * 200,
                managed_money_short=50_000.0,
            )
        )
    return records


@pytest.mark.asyncio
async def test_run_reports_unavailable_without_cot_data(db):
    result = await positioning_agent.run(db, datetime(2026, 6, 5, tzinfo=UTC), ingest_first=False)
    assert result.status == "unavailable"


@pytest.mark.asyncio
async def test_run_summarizes_when_data_exists(db):
    records = _cot_records()
    persist_cot_records(db, records)
    db.commit()

    as_of = records[-1].observed_at + timedelta(days=3)
    result = await positioning_agent.run(db, as_of, ingest_first=False)
    assert result.status == "ok"
    assert result.data["cot"]["cot_net_speculative_position"] is not None
