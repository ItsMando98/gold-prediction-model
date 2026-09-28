"""Agent 5 -- Regime Agent (plan section 50).

Responsibilities: classify regime, detect regime changes. Persists a
RegimeSnapshot on every run (the ``regimes`` table existed from Sprint 1
but nothing wrote to it until this agent) so regime history and
transitions can be queried directly instead of only being embedded inside
individual Prediction rows.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.agents.base import AgentResult
from packages.common.db.models import RegimeSnapshot
from packages.regimes.classifier import RegimeResult, classify_regime


def _last_regime(session: Session, symbol: str, before: datetime) -> RegimeSnapshot | None:
    stmt = (
        select(RegimeSnapshot)
        .where(RegimeSnapshot.symbol == symbol)
        .where(RegimeSnapshot.as_of < before)
        .order_by(RegimeSnapshot.as_of.desc())
        .limit(1)
    )
    return session.execute(stmt).scalars().first()


async def run(
    session: Session, symbol: str, as_of: datetime, features: dict[str, float | None]
) -> AgentResult:
    result: RegimeResult = classify_regime(features)
    previous = _last_regime(session, symbol, as_of)

    snapshot = RegimeSnapshot(
        symbol=symbol,
        as_of=as_of,
        regime=result.regime.value,
        scores={**result.scores, "rationale": result.rationale},
        created_at=datetime.now(UTC),
    )
    session.add(snapshot)
    session.commit()

    changed = previous is not None and previous.regime != result.regime.value
    detail = f"regime={result.regime.value}"
    if changed:
        detail += f" (changed from {previous.regime})"

    return AgentResult(
        agent="regime",
        status="ok",
        detail=detail,
        data={
            "regime": result.regime.value,
            "previous_regime": previous.regime if previous else None,
            "changed": changed,
            "snapshot_id": snapshot.id,
        },
    )
