"""Combines the deterministic score with an active ML model's probability
(plan section 25, "Ensemble").

Inactive by construction: ``score_with_active_model`` returns ``(None,
None)`` until a ``ModelVersion`` row with ``status="active"`` actually
exists, which only happens after real historical training data has been
backfilled and a model has been trained, evaluated, and promoted (see
``packages/models/train.py`` and ``docs/ROADMAP.md``). No model trained on
synthetic/fixture data is ever marked active outside of tests.
"""

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.common.db.models import ModelVersion
from packages.models.io import load_model


def get_active_model_version(session: Session) -> ModelVersion | None:
    stmt = (
        select(ModelVersion)
        .where(ModelVersion.status == "active")
        .order_by(ModelVersion.trained_at.desc())
        .limit(1)
    )
    return session.execute(stmt).scalars().first()


def build_feature_vector(features: dict[str, float | None], feature_names: list[str]) -> np.ndarray:
    """Missing features are imputed as 0.0 -- a documented simplification;
    a production trainer would carry a real imputer alongside the model."""
    row = [features.get(name) if features.get(name) is not None else 0.0 for name in feature_names]
    return np.array([row], dtype=float)


def score_with_active_model(
    session: Session, features: dict[str, float | None]
) -> tuple[float | None, ModelVersion | None]:
    """Returns (P(down), the ModelVersion used), or (None, None) if no active model."""
    version = get_active_model_version(session)
    if version is None:
        return None, None

    feature_names = version.metrics.get("feature_names") or []
    if not feature_names or not version.artifact_path:
        return None, None

    model = load_model(version.artifact_path)
    if model is None:
        return None, None

    x = build_feature_vector(features, feature_names)
    proba = model.predict_proba(x)
    return float(proba[0]), version


def combine(deterministic_score: float, ml_probability: float | None, weight_ml: float = 0.3) -> float:
    """Weighted blend of the deterministic 0-100 score and an ML down-probability
    (expressed on the same 0-100 scale). Falls back to the deterministic score
    alone when no ML probability is available. ``weight_ml`` is a starting
    assumption, not yet validated -- plan section 25: "weights must be
    learned/validated rather than permanently hard-coded"."""
    if ml_probability is None:
        return deterministic_score
    ml_as_score = ml_probability * 100.0
    return (1.0 - weight_ml) * deterministic_score + weight_ml * ml_as_score
