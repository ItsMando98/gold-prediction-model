"""Agent 4 -- News Event Agent (plan section 50).

Responsibilities: news ingestion, event extraction, deduplication, causal
mapping. Extraction is genuinely LLM-backed (Claude via
``client.messages.parse`` against the ``NewsEvent`` schema -- plan section
58: "LLM output must conform to Pydantic schema"). The agent is never
asked to freely decide a trading direction; it can only answer through the
typed ``transmission_chain`` contract in
packages/common/schemas/news_event.py, and its confidence is capped by
source tier (plan section 19) on the way into the database regardless of
what it reports.

The Anthropic client is dependency-injected everywhere so tests never make
a live call -- see tests/unit/test_news_event_agent.py.
"""

from datetime import datetime

import anthropic
from sqlalchemy.orm import Session

from packages.agents.base import AgentResult
from packages.common.config import get_settings
from packages.common.schemas import NewsEvent
from packages.ingestion.base import ProviderError
from packages.ingestion.store import persist_news_article, persist_news_event

SYSTEM_PROMPT = """You are the News Event Agent for a gold (XAUUSD) market intelligence system.

Read the article and identify at most one primary market-moving event relevant to gold.
Express your read of it as an explicit, ordered causal transmission chain from the event
to gold, ending in exactly "gold_up" or "gold_down" -- never a bare sentiment label.
Multiple transmission channels can exist for the same event (e.g. a geopolitical shock can
move gold up via safe-haven demand, or down via an oil-driven hawkish repricing of Fed
policy). You are told the currently prevailing market regime -- pick the single channel
most likely to dominate under that regime, not just the first one that comes to mind.
Be conservative: if the article has no material, gold-relevant event, still return your
best-effort single most plausible chain, but set relevance and confidence low.
This is structured research input only, never a trade recommendation.
"""


def get_client() -> anthropic.Anthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ProviderError("anthropic", "ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def classify_article(
    client: anthropic.Anthropic,
    *,
    headline: str,
    body: str | None,
    source: str,
    published_at: datetime,
    current_regime: str,
    model: str = "claude-opus-5",
) -> NewsEvent:
    """Send one article to Claude and get back a validated NewsEvent."""
    article_text = f"Headline: {headline}\n\n{body or ''}".strip()
    user_message = (
        f"Current regime: {current_regime}\n"
        f"Source: {source}\n"
        f"Published: {published_at.isoformat()}\n\n"
        f"{article_text}"
    )
    try:
        response = client.messages.parse(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            output_format=NewsEvent,
        )
    except anthropic.APIError as exc:
        raise ProviderError("anthropic", f"news classification failed: {exc}", cause=exc) from exc
    return response.parsed_output


async def process_article(
    session: Session,
    client: anthropic.Anthropic,
    *,
    source: str,
    headline: str,
    body: str | None,
    url: str | None,
    published_at: datetime,
    current_regime: str,
    model: str | None = None,
) -> AgentResult:
    """Ingest one article and classify it, unless it's a dedup hit on an
    already-classified article."""
    model = model or get_settings().agent_model

    article = persist_news_article(
        session, source=source, headline=headline, body=body, url=url, published_at=published_at
    )
    if article.events:
        session.commit()
        return AgentResult(
            agent="news_event",
            status="ok",
            detail="article already classified (dedup hit)",
            data={"article_id": article.id, "event_id": article.events[0].id},
        )

    event = classify_article(
        client,
        headline=headline,
        body=body,
        source=source,
        published_at=published_at,
        current_regime=current_regime,
        model=model,
    )
    record = persist_news_event(session, article=article, event=event, model=model)
    session.commit()

    return AgentResult(
        agent="news_event",
        status="ok",
        detail=f"classified '{event.event}' -> {event.gold_direction} (confidence {record.confidence:.2f})",
        data={"article_id": article.id, "event_id": record.id},
    )


async def run(session: Session, as_of: datetime, current_regime: str) -> AgentResult:
    """No live news feed is wired up yet (see docs/ROADMAP.md). The real capability
    here is `process_article`, meant to be called per-article by whatever news feed
    is eventually connected -- `run` reports that honestly rather than pretending to
    have polled anything."""
    return AgentResult(
        agent="news_event",
        status="unavailable",
        detail="no live news feed configured; call process_article directly for a known article",
        data={},
    )
