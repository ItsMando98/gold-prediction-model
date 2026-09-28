from datetime import UTC, datetime

import pytest

from packages.agents import news_event_agent
from packages.common.schemas import NewsEvent, NewsEventCategory
from tests.anthropic_fakes import FakeParseClient


def _fake_event() -> NewsEvent:
    return NewsEvent(
        event="Hormuz escalation",
        category=NewsEventCategory.MIDDLE_EAST,
        entities=["Iran"],
        direct_assets=["Brent"],
        transmission_chain=["oil_up", "gold_down"],
        relevance=0.8,
        confidence=0.85,
        rationale="Oil supply risk repriced Fed hawkishness.",
    )


@pytest.mark.asyncio
async def test_process_article_persists_article_and_event(db):
    client = FakeParseClient(parsed_output=_fake_event())
    result = await news_event_agent.process_article(
        db,
        client,
        source="Reuters",
        headline="Iran threatens Hormuz closure",
        body="Details...",
        url=None,
        published_at=datetime(2026, 6, 5, tzinfo=UTC),
        current_regime="MIXED",
        model="claude-opus-5",
    )
    assert result.status == "ok"
    assert "Hormuz escalation" in result.detail
    assert result.data["article_id"]
    assert result.data["event_id"]


@pytest.mark.asyncio
async def test_process_article_dedup_hit_does_not_reclassify(db):
    client = FakeParseClient(parsed_output=_fake_event())
    kwargs = dict(
        source="Reuters",
        headline="Iran threatens Hormuz closure",
        body="Details...",
        url=None,
        published_at=datetime(2026, 6, 5, tzinfo=UTC),
        current_regime="MIXED",
    )
    first = await news_event_agent.process_article(db, client, **kwargs)
    second = await news_event_agent.process_article(db, client, **kwargs)

    assert first.data["article_id"] == second.data["article_id"]
    assert "dedup hit" in second.detail
    assert len(client.messages.calls) == 1  # only classified once
