from datetime import UTC, datetime

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


def test_classify_article_returns_parsed_event():
    client = FakeParseClient(parsed_output=_fake_event())
    event = news_event_agent.classify_article(
        client,
        headline="Iran threatens Hormuz closure",
        body="Details...",
        source="Reuters",
        published_at=datetime(2026, 6, 5, tzinfo=UTC),
        current_regime="RATES_DOMINATED_BEARISH",
    )
    assert event.event == "Hormuz escalation"
    assert event.gold_direction == "gold_down"

    # the current regime is passed through to the model as context
    call = client.messages.calls[0]
    assert "RATES_DOMINATED_BEARISH" in call["messages"][0]["content"]
    assert call["output_format"] is NewsEvent
