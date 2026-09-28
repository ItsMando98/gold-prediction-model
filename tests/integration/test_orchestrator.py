from datetime import UTC, datetime, timedelta

import pytest

from packages.agents.orchestrator import NewsArticleInput, run_weekly_pipeline
from packages.common.db.models import Prediction
from packages.common.schemas import NewsEvent, NewsEventCategory
from packages.ingestion.store import persist_bars, persist_observations
from tests.anthropic_fakes import FakeCreateClient, FakeParseClient
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


class _MultiClient:
    """Routes .messages.parse() to one fake and .messages.create() to another,
    so a single object can serve as both the news and explanation agent's client."""

    def __init__(self, parse_client, create_client):
        self._parse = parse_client
        self._create = create_client
        self.messages = self

    def parse(self, **kwargs):
        return self._parse.messages.parse(**kwargs)

    def create(self, **kwargs):
        return self._create.messages.create(**kwargs)


@pytest.mark.asyncio
async def test_full_pipeline_persists_one_prediction_with_narrative_and_regime(db):
    _seed_bearish_scenario(db)

    fake_event = NewsEvent(
        event="Hormuz escalation",
        category=NewsEventCategory.MIDDLE_EAST,
        entities=["Iran"],
        direct_assets=["Brent"],
        transmission_chain=["oil_up", "gold_down"],
        relevance=0.7,
        confidence=0.8,
        rationale="Oil supply risk.",
    )
    client = _MultiClient(
        FakeParseClient(parsed_output=fake_event),
        FakeCreateClient(text="Gold is pressured by rising real yields and a firmer dollar."),
    )

    articles = [
        NewsArticleInput(
            source="Reuters",
            headline="Iran threatens Hormuz closure",
            body="Details...",
            url=None,
            published_at=FRIDAY_CLOSE - timedelta(hours=6),
        )
    ]

    report = await run_weekly_pipeline(
        db,
        as_of=FRIDAY_CLOSE,
        ingest_market_data=False,
        news_articles=articles,
        anthropic_client=client,
    )

    assert report.prediction is not None
    assert report.prediction.bias == "bearish"
    assert report.prediction.narrative == "Gold is pressured by rising real yields and a firmer dollar."

    agent_names = {r.agent for r in report.agent_results}
    assert {"positioning", "rates_macro", "news_event", "prediction", "regime", "explanation"} <= agent_names

    # only one prediction row was ever inserted
    count = db.query(Prediction).filter_by(id=report.prediction.id).count()
    assert count == 1


@pytest.mark.asyncio
async def test_pipeline_without_news_or_narrative_still_persists(db):
    _seed_bearish_scenario(db)

    report = await run_weekly_pipeline(
        db, as_of=FRIDAY_CLOSE, ingest_market_data=False, news_articles=None, generate_narrative=False
    )
    assert report.prediction is not None
    assert report.prediction.narrative is None
    assert not any(r.agent == "news_event" and r.status == "ok" for r in report.agent_results)


@pytest.mark.asyncio
async def test_missing_anthropic_api_key_does_not_block_persistence(db):
    """No client injected and no ANTHROPIC_API_KEY configured in this test
    environment -> explanation_agent.get_client() raises ProviderError, which
    the orchestrator downgrades to a best-effort skip rather than letting it
    take down the whole (already-computed) prediction."""
    _seed_bearish_scenario(db)

    report = await run_weekly_pipeline(db, as_of=FRIDAY_CLOSE, generate_narrative=True)

    assert report.prediction is not None
    assert report.prediction.narrative is None
    explanation_result = next(r for r in report.agent_results if r.agent == "explanation")
    assert explanation_result.status == "error"
    assert "ANTHROPIC_API_KEY" in explanation_result.detail


@pytest.mark.asyncio
async def test_unexpected_explanation_error_is_not_silently_swallowed(db):
    """Only ProviderError (the expected, wrapped failure mode) is downgraded to
    a best-effort skip -- an unrelated bug must still fail loudly rather than
    quietly produce a prediction with no narrative and no visible error."""
    _seed_bearish_scenario(db)

    class BrokenClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("this is not a provider error")

    with pytest.raises(RuntimeError):
        await run_weekly_pipeline(db, as_of=FRIDAY_CLOSE, anthropic_client=BrokenClient())
