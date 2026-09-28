from datetime import UTC, datetime

from packages.features.context import FeatureContext
from packages.features.definitions.news import news_aggregate


def _ctx(events):
    return FeatureContext(as_of=datetime(2026, 6, 5, tzinfo=UTC), news=events)


def test_no_events_returns_none():
    result = news_aggregate(_ctx([]))
    assert result["news_net_score"] is None
    assert result["news_event_count"] == 0


def test_single_bearish_event():
    events = [{"transmission_chain": ["oil_up", "gold_down"], "confidence": 0.8, "relevance": 0.9}]
    result = news_aggregate(_ctx(events))
    assert result["news_net_score"] == 0.8 * 0.9
    assert result["news_event_count"] == 1
    assert result["news_max_confidence"] == 0.8


def test_single_bullish_event_is_negative():
    events = [{"transmission_chain": ["safe_haven_demand", "gold_up"], "confidence": 0.6, "relevance": 0.5}]
    result = news_aggregate(_ctx(events))
    assert result["news_net_score"] == -0.6 * 0.5


def test_conflicting_events_partially_cancel():
    events = [
        {"transmission_chain": ["gold_down"], "confidence": 0.8, "relevance": 1.0},
        {"transmission_chain": ["gold_up"], "confidence": 0.8, "relevance": 1.0},
    ]
    result = news_aggregate(_ctx(events))
    assert result["news_net_score"] == 0.0


def test_malformed_events_without_chain_are_skipped():
    events = [{"transmission_chain": [], "confidence": 0.9, "relevance": 0.9}]
    result = news_aggregate(_ctx(events))
    assert result["news_net_score"] is None
    assert result["news_event_count"] == 1
