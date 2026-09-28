"""Agent Team orchestrator (plan section 50): coordinates all 8 specialist
agents into the weekly Friday prediction pipeline.

    MarketDataAgent -> RatesMacroAgent -> PositioningAgent -> NewsEventAgent
    -> PredictionAgent -> RegimeAgent -> ExplanationAgent -> persist

This is the enriched alternative to calling
``packages.snapshots.friday.generate_prediction`` directly: it adds real
CFTC positioning, classified news events, a persisted regime snapshot with
change detection, an optional active-ML-model blend, and a narrative --
none of which the bare deterministic path produces on its own. The
underlying score is still the same deterministic/ensemble computation;
this module only adds orchestration, not a second opinion.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import anthropic
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.agents import (
    explanation_agent,
    market_data_agent,
    news_event_agent,
    positioning_agent,
    prediction_agent,
    rates_macro_agent,
    regime_agent,
)
from packages.agents.base import AgentResult
from packages.common.db.models import Prediction, RegimeSnapshot
from packages.common.logging import get_logger
from packages.ingestion.base import ProviderError
from packages.snapshots.friday import most_recent_friday_close, persist_prediction_payload

logger = get_logger(__name__)


@dataclass
class NewsArticleInput:
    """One article for the News Event Agent to classify this run."""

    source: str
    headline: str
    body: str | None
    url: str | None
    published_at: datetime


@dataclass
class PipelineReport:
    agent_results: list[AgentResult] = field(default_factory=list)
    prediction: Prediction | None = None


def _last_known_regime(session: Session, symbol: str, before: datetime) -> str:
    stmt = (
        select(RegimeSnapshot.regime)
        .where(RegimeSnapshot.symbol == symbol)
        .where(RegimeSnapshot.as_of < before)
        .order_by(RegimeSnapshot.as_of.desc())
        .limit(1)
    )
    regime = session.execute(stmt).scalar_one_or_none()
    return regime or "MIXED"


async def run_weekly_pipeline(
    session: Session,
    *,
    as_of: datetime | None = None,
    symbol: str = "XAUUSD",
    horizon: str = "weekend_to_monday_close",
    ingest_market_data: bool = False,
    news_articles: list[NewsArticleInput] | None = None,
    anthropic_client: anthropic.Anthropic | None = None,
    generate_narrative: bool = True,
) -> PipelineReport:
    """Run the full Agent Team pipeline and persist one immutable Prediction."""
    reference = as_of or datetime.now(UTC)
    friday_close = most_recent_friday_close(reference)
    report = PipelineReport()

    if ingest_market_data:
        report.agent_results.append(
            await market_data_agent.run(session, friday_close - timedelta(days=10), friday_close)
        )
    report.agent_results.append(
        await positioning_agent.run(session, friday_close, ingest_first=ingest_market_data)
    )
    report.agent_results.append(await rates_macro_agent.run(session, friday_close))

    if news_articles:
        client = anthropic_client or news_event_agent.get_client()
        current_regime = _last_known_regime(session, symbol, friday_close)
        for article in news_articles:
            report.agent_results.append(
                await news_event_agent.process_article(
                    session,
                    client,
                    source=article.source,
                    headline=article.headline,
                    body=article.body,
                    url=article.url,
                    published_at=article.published_at,
                    current_regime=current_regime,
                )
            )

    prediction_result, payload = await prediction_agent.run(
        session, as_of=friday_close, horizon=horizon, symbol=symbol
    )
    report.agent_results.append(prediction_result)
    report.agent_results.append(await regime_agent.run(session, symbol, friday_close, payload.features))

    if generate_narrative:
        try:
            client = anthropic_client or explanation_agent.get_client()
            payload.narrative = explanation_agent.explain(client, payload)
            report.agent_results.append(
                AgentResult(agent="explanation", status="ok", detail="narrative generated")
            )
        except ProviderError as exc:
            # Best-effort: a missing key or a transient API failure should not block
            # the numeric prediction itself from being produced and persisted.
            logger.warning("explanation_agent_failed", error=str(exc))
            report.agent_results.append(AgentResult(agent="explanation", status="error", detail=str(exc)))

    report.prediction = persist_prediction_payload(session, payload)
    return report
