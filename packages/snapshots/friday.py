"""Friday snapshot generator (plan sections 9, 30, 36, 87 Task 9).

Builds the "Friday close -> Monday" baseline prediction: a point-in-time
feature snapshot as of Friday's close, the rule-based regime, the
deterministic Gold Risk Score, and an immutable Prediction record. This is
the object the first milestone (plan section 88) is judged against.

Weekend re-scoring (Saturday/Sunday news updates, plan section 37) is a
separate follow-up step -- see docs/ROADMAP.md -- that would call
``generate_prediction`` again with the same Friday feature snapshot but
updated event inputs and diff the result against this baseline.
"""

import subprocess
from datetime import UTC, datetime, time, timedelta

from sqlalchemy.orm import Session

from packages.common.db.models import Prediction, PredictionDriver
from packages.features.data_access import price_series
from packages.features.engine import FEATURE_SET_VERSION, generate_snapshot
from packages.regimes.classifier import classify_regime
from packages.signals.confidence import compute_confidence
from packages.signals.deterministic import compute_deterministic_score
from packages.signals.invalidation import build_confirmation_invalidation
from packages.signals.key_levels import compute_key_levels

CONFIG_VERSION = "v1"


def _bias_from_score(score: float) -> str:
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


def generate_prediction(
    session: Session,
    *,
    as_of: datetime | None = None,
    horizon: str = "weekend_to_monday_close",
    symbol: str = "XAUUSD",
) -> Prediction:
    """Generate and persist an immutable prediction as of a Friday close."""
    reference = as_of or datetime.now(UTC)
    friday_close = most_recent_friday_close(reference)
    target_time = friday_close + timedelta(days=3)  # Monday, same time-of-day

    snapshot = generate_snapshot(session, symbol, friday_close)
    features = snapshot.features

    regime_result = classify_regime(features)
    score_result = compute_deterministic_score(features)
    confidence = compute_confidence(score_result.components, regime_result.regime)
    bias = _bias_from_score(score_result.risk_score)

    xau_df = price_series(session, symbol, friday_close)
    key_levels = compute_key_levels(xau_df)
    confirmations, invalidation = build_confirmation_invalidation(bias, key_levels)

    contradictions = [
        f"{c.name}: {', '.join(c.drivers)}"
        for c in score_result.components
        if c.available
        and (
            (bias == "bearish" and c.score < 45)
            or (bias == "bullish" and c.score > 55)
        )
    ]

    prediction = Prediction(
        created_at=datetime.now(UTC),
        target_time=target_time,
        horizon=horizon,
        symbol=symbol,
        regime=regime_result.regime.value,
        probabilities={},  # deliberately empty -- see module docstring / plan section 26 & 32
        risk_score=score_result.risk_score,
        bias=bias,
        confidence=confidence,
        confirmations=confirmations,
        contradictions=contradictions,
        key_levels=key_levels,
        event_risks=[],  # populated once the macro calendar (phase 3) exists
        invalidation=invalidation,
        model_versions={
            "feature_set_version": FEATURE_SET_VERSION,
            "regime_classifier": "rule_based_v1",
            "deterministic_score": "v1",
            "calibrated": False,
        },
        feature_snapshot_id=snapshot.id,
        config_version=CONFIG_VERSION,
        code_commit=_code_commit(),
    )
    session.add(prediction)
    session.flush()

    for component in score_result.components:
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
