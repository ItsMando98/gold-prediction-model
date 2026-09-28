"""Friday snapshot generator (plan sections 9, 30, 36, 87 Task 9).

Builds the "Friday close -> Monday" baseline prediction: a point-in-time
feature snapshot as of Friday's close, the rule-based regime, the
deterministic Gold Risk Score, and an immutable Prediction record. This is
the object the first milestone (plan section 88) is judged against.

Construction is split from persistence (``build_prediction_payload`` /
``persist_prediction_payload``) so the Agent Team orchestrator
(packages/agents/orchestrator.py) can fold in the Explanation Agent's
narrative and an active ML model's score *before* the one and only INSERT
-- a Prediction is never updated in place (plan section 27), so anything
that should be part of it has to exist before that insert, not after.
``generate_prediction`` remains the simple one-call path (build + persist,
no narrative/ML) for direct/test use.

Weekend re-scoring (Saturday/Sunday news updates, plan section 37) is a
separate follow-up step -- see docs/ROADMAP.md -- that would call this
module again with the same Friday feature snapshot but updated event
inputs and diff the result against this baseline.
"""

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta

from sqlalchemy.orm import Session

from packages.common.db.models import Prediction, PredictionDriver
from packages.features.data_access import price_series
from packages.features.engine import FEATURE_SET_VERSION, generate_snapshot
from packages.regimes.classifier import classify_regime
from packages.signals.confidence import compute_confidence
from packages.signals.deterministic import ComponentScore, compute_deterministic_score
from packages.signals.invalidation import build_confirmation_invalidation
from packages.signals.key_levels import compute_key_levels

CONFIG_VERSION = "v1"


@dataclass
class PredictionPayload:
    """Everything needed to construct a Prediction row, before it's inserted."""

    symbol: str
    horizon: str
    target_time: datetime
    regime: str
    risk_score: float
    bias: str
    confidence: float
    confirmations: list[str]
    contradictions: list[str]
    key_levels: dict
    invalidation: list[str]
    model_versions: dict
    feature_snapshot_id: str
    features: dict = field(repr=False)
    components: list[ComponentScore] = field(repr=False)
    config_version: str = CONFIG_VERSION
    code_commit: str | None = None
    narrative: str | None = None
    ml_score: float | None = None
    event_risks: list = field(default_factory=list)


def bias_from_score(score: float) -> str:
    if score <= 40:
        return "bullish"
    if score >= 60:
        return "bearish"
    return "neutral"


def _code_commit() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return None


def most_recent_friday_close(reference: datetime) -> datetime:
    """Most recent Friday ~market close (21:00 UTC / ~17:00 ET) at or before ``reference``."""
    days_since_friday = (reference.weekday() - 4) % 7
    friday_date = reference.date() - timedelta(days=days_since_friday)
    candidate = datetime.combine(friday_date, time(21, 0), tzinfo=UTC)
    if candidate > reference:
        candidate -= timedelta(days=7)
    return candidate


def build_prediction_payload(
    session: Session,
    *,
    as_of: datetime | None = None,
    horizon: str = "weekend_to_monday_close",
    symbol: str = "XAUUSD",
) -> PredictionPayload:
    """Compute (but do not persist) everything a Prediction row needs."""
    reference = as_of or datetime.now(UTC)
    friday_close = most_recent_friday_close(reference)
    target_time = friday_close + timedelta(days=3)  # Monday, same time-of-day

    snapshot = generate_snapshot(session, symbol, friday_close)
    features = snapshot.features

    regime_result = classify_regime(features)
    score_result = compute_deterministic_score(features)
    confidence = compute_confidence(score_result.components, regime_result.regime)
    bias = bias_from_score(score_result.risk_score)

    xau_df = price_series(session, symbol, friday_close)
    key_levels = compute_key_levels(xau_df)
    confirmations, invalidation = build_confirmation_invalidation(bias, key_levels)

    contradictions = [
        f"{c.name}: {', '.join(c.drivers)}"
        for c in score_result.components
        if c.available and ((bias == "bearish" and c.score < 45) or (bias == "bullish" and c.score > 55))
    ]

    return PredictionPayload(
        symbol=symbol,
        horizon=horizon,
        target_time=target_time,
        regime=regime_result.regime.value,
        risk_score=score_result.risk_score,
        bias=bias,
        confidence=confidence,
        confirmations=confirmations,
        contradictions=contradictions,
        key_levels=key_levels,
        invalidation=invalidation,
        model_versions={
            "feature_set_version": FEATURE_SET_VERSION,
            "regime_classifier": "rule_based_v1",
            "deterministic_score": "v1",
            "calibrated": False,
        },
        feature_snapshot_id=snapshot.id,
        features=features,
        components=score_result.components,
        code_commit=_code_commit(),
    )


def persist_prediction_payload(session: Session, payload: PredictionPayload) -> Prediction:
    """The single INSERT that makes a prediction exist. Never called twice for the
    same payload, and the row is never updated afterward."""
    model_versions = dict(payload.model_versions)
    if payload.ml_score is not None:
        model_versions["ml_score_available"] = True

    prediction = Prediction(
        created_at=datetime.now(UTC),
        target_time=payload.target_time,
        horizon=payload.horizon,
        symbol=payload.symbol,
        regime=payload.regime,
        probabilities={},  # deliberately empty -- see module docstring / plan section 26 & 32
        risk_score=payload.risk_score,
        bias=payload.bias,
        confidence=payload.confidence,
        confirmations=payload.confirmations,
        contradictions=payload.contradictions,
        key_levels=payload.key_levels,
        event_risks=payload.event_risks,
        invalidation=payload.invalidation,
        model_versions=model_versions,
        feature_snapshot_id=payload.feature_snapshot_id,
        config_version=payload.config_version,
        code_commit=payload.code_commit,
        narrative=payload.narrative,
        ml_score=payload.ml_score,
    )
    session.add(prediction)
    session.flush()

    for component in payload.components:
        session.add(
            PredictionDriver(
                prediction_id=prediction.id,
                name=component.name,
                category=component.name,
                contribution=component.contribution,
                description=(
                    "; ".join(component.drivers)
                    if component.drivers
                    else ("no data available" if not component.available else "neutral")
                ),
            )
        )

    session.commit()
    session.refresh(prediction)
    return prediction


def generate_prediction(
    session: Session,
    *,
    as_of: datetime | None = None,
    horizon: str = "weekend_to_monday_close",
    symbol: str = "XAUUSD",
) -> Prediction:
    """Build and persist an immutable prediction in one call (no narrative/ML score).

    Use ``packages.agents.orchestrator.run_weekly_pipeline`` instead when you want
    the full Agent Team (positioning, news, explanation, active ML model).
    """
    payload = build_prediction_payload(session, as_of=as_of, horizon=horizon, symbol=symbol)
    return persist_prediction_payload(session, payload)
