"""Agent 3 -- Positioning Agent (plan section 50).

Responsibilities: COT, ETF flows, options, open interest. ETF flows and
options have no free data source wired up yet (see docs/ROADMAP.md); COT
ingestion + crowding/liquidation-risk summarization is real.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from packages.agents.base import AgentResult
from packages.features.context import FeatureContext
from packages.features.data_access import cot_series
from packages.features.definitions.positioning import cot_positioning
from packages.ingestion.pipeline import ingest_positioning_history
from packages.ingestion.providers.cftc_cot import CftcCotProvider

_COT_SYMBOLS = ("GC",)


async def ingest(session: Session, start: datetime, end: datetime) -> dict[str, int]:
    provider = CftcCotProvider()
    try:
        return await ingest_positioning_history(session, [provider], list(_COT_SYMBOLS), start, end)
    finally:
        await provider.aclose()


def summarize(session: Session, as_of: datetime, symbol: str = "GC") -> dict[str, float | None]:
    ctx = FeatureContext(as_of=as_of, cot={symbol: cot_series(session, symbol, as_of, lookback_days=1200)})
    return cot_positioning(ctx)


async def run(session: Session, as_of: datetime, *, ingest_first: bool = False) -> AgentResult:
    if ingest_first:
        await ingest(session, as_of - timedelta(days=30), as_of)

    summary = summarize(session, as_of)
    has_data = summary.get("cot_net_speculative_position") is not None
    return AgentResult(
        agent="positioning",
        status="ok" if has_data else "unavailable",
        detail=(
            "COT positioning summarized" if has_data else "no COT positioning data available for this as_of"
        )
        + "; ETF flows / options open interest have no free data source configured yet",
        data={"cot": summary},
    )
