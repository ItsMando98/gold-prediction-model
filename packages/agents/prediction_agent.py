"""Agent 6 -- Prediction Agent (plan section 50).

Responsibilities: assemble features, execute models, create forecast.
Builds the deterministic-score payload (packages/snapshots/friday.py) and,
if a real trained ModelVersion is active, blends in its probability
(packages/models/ensemble.py) before anything is persisted -- persistence
itself is the orchestrator's job, so the same payload can still be handed
to the Explanation Agent for a narrative first (plan section 27: a
Prediction is immutable, so anything that should be part of it must exist
before the one INSERT, not patched in after).

If the ML blend moves the score across a bias boundary (plan section 26
buckets), bias/confirmation/invalidation/contradictions are recomputed
against the *blended* score -- leaving them keyed to the pre-ensemble
score would produce a payload whose narrative text disagrees with its own
risk_score.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from packages.agents.base import AgentResult
from packages.models.ensemble import combine, score_with_active_model
from packages.signals.invalidation import build_confirmation_invalidation
from packages.signals.scoring import clamp
from packages.snapshots.friday import PredictionPayload, bias_from_score, build_prediction_payload


async def run(
    session: Session,
    *,
    as_of: datetime | None = None,
    horizon: str = "weekend_to_monday_close",
    symbol: str = "XAUUSD",
) -> tuple[AgentResult, PredictionPayload]:
    payload = build_prediction_payload(session, as_of=as_of, horizon=horizon, symbol=symbol)

    ml_probability, model_version = score_with_active_model(session, payload.features)
    if ml_probability is not None and model_version is not None:
        blended_score = clamp(combine(payload.risk_score, ml_probability))
        blended_bias = bias_from_score(blended_score)

        if blended_bias != payload.bias:
            confirmations, invalidation = build_confirmation_invalidation(blended_bias, payload.key_levels)
            payload.confirmations = confirmations
            payload.invalidation = invalidation
            payload.contradictions = [
                f"{c.name}: {', '.join(c.drivers)}"
                for c in payload.components
                if c.available
                and (
                    (blended_bias == "bearish" and c.score < 45)
                    or (blended_bias == "bullish" and c.score > 55)
                )
            ]

        payload.risk_score = blended_score
        payload.bias = blended_bias
        payload.ml_score = ml_probability
        payload.model_versions["ml_model_id"] = model_version.id
        payload.model_versions["ml_model_type"] = model_version.model_type
        detail = (
            f"deterministic + ML ensemble (model {model_version.name}, "
            f"P(down)={ml_probability:.2f}) -> risk_score={payload.risk_score:.1f}"
        )
    else:
        detail = f"deterministic-only score (no active ML model) -> risk_score={payload.risk_score:.1f}"

    result = AgentResult(
        agent="prediction",
        status="ok",
        detail=detail,
        data={"risk_score": payload.risk_score, "regime": payload.regime, "ml_score": payload.ml_score},
    )
    return result, payload
