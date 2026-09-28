"""Walk-forward training/evaluation and the ModelVersion registry (plan
sections 29, 62, phase 9).

``train_and_register`` always writes ``status="candidate"`` -- promoting a
model to ``"active"`` (the only status ``packages.models.ensemble`` will
read) is a deliberate separate step a human takes after reviewing
walk-forward metrics, never something this pipeline does to itself (plan
section 86: "Backtest before live trust").
"""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from packages.backtesting.dataset import feature_columns
from packages.backtesting.metrics import classification_metrics
from packages.backtesting.walk_forward import walk_forward_splits
from packages.common.db.models import ModelVersion
from packages.features.engine import FEATURE_SET_VERSION
from packages.models.baseline import MODEL_REGISTRY
from packages.models.io import save_model


def _prepare_xy(
    df: pd.DataFrame, feature_cols: list[str], label_col: str
) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    subset = df.dropna(subset=[label_col])
    x = subset[feature_cols].fillna(0.0).to_numpy(dtype=float)
    y = subset[label_col].to_numpy(dtype=float)
    return x, y, pd.DatetimeIndex(subset.index)


def walk_forward_evaluate(
    df: pd.DataFrame,
    model_type: str,
    *,
    label_col: str = "label_down_5d",
    train_years: float = 3.0,
    validation_years: float = 1.0,
    test_years: float = 1.0,
) -> dict:
    """Fits a fresh model per fold and evaluates it on that fold's held-out
    test window. Returns fold-averaged metrics; fits no final model (see
    ``train_and_register`` for that)."""
    feature_cols = feature_columns(df)
    x, y, dates = _prepare_xy(df, feature_cols, label_col)

    fold_metrics = []
    for split in walk_forward_splits(dates, train_years, validation_years, test_years):
        train_mask = dates.isin(split.train_index)
        test_mask = dates.isin(split.test_index)
        if train_mask.sum() < 10 or test_mask.sum() < 1:
            continue
        model = MODEL_REGISTRY[model_type]()
        model.fit(x[train_mask], y[train_mask])
        proba = model.predict_proba(x[test_mask])
        fold_metrics.append(classification_metrics(y[test_mask], proba))

    result: dict = {"folds": len(fold_metrics), "feature_names": feature_cols, "label_col": label_col}
    for key in ("auc", "pr_auc", "brier", "log_loss"):
        values = [m[key] for m in fold_metrics if m.get(key) is not None]
        result[key] = float(np.mean(values)) if values else None
    return result


def train_and_register(
    session: Session,
    df: pd.DataFrame,
    model_type: str,
    *,
    name: str,
    label_col: str = "label_down_5d",
) -> ModelVersion:
    """Walk-forward evaluates, then fits ``model_type`` on the full dataset and
    registers it as a ``status="candidate"`` ModelVersion."""
    if model_type not in MODEL_REGISTRY:
        raise ValueError(f"unknown model_type {model_type!r}, must be one of {list(MODEL_REGISTRY)}")

    feature_cols = feature_columns(df)
    x, y, dates = _prepare_xy(df, feature_cols, label_col)
    if len(y) == 0:
        raise ValueError("no labeled rows to train on")

    metrics = walk_forward_evaluate(df, model_type, label_col=label_col)

    model = MODEL_REGISTRY[model_type]()
    model.fit(x, y)

    artifact_name = f"{name}_{model_type}_{datetime.now(UTC):%Y%m%dT%H%M%S}"
    artifact_path = save_model(model, name=artifact_name)

    version = ModelVersion(
        name=name,
        model_type=model_type,
        feature_set_version=FEATURE_SET_VERSION,
        trained_at=datetime.now(UTC),
        training_window_start=dates.min().to_pydatetime(),
        training_window_end=dates.max().to_pydatetime(),
        metrics={**metrics, "feature_names": feature_cols, "label_col": label_col},
        status="candidate",
        artifact_path=artifact_path,
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version
