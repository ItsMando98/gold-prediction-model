import numpy as np
import pandas as pd
import pytest

from packages.models.io import load_model
from packages.models.train import train_and_register, walk_forward_evaluate


def _synthetic_df(n=2200, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2015-01-01", periods=n, freq="D")
    feature_a = rng.normal(0, 1, n)
    feature_b = rng.normal(0, 1, n)
    noise = rng.normal(0, 0.5, n)
    logit = feature_a * 1.5 - feature_b * 0.5 + noise
    prob = 1 / (1 + np.exp(-logit))
    label = (rng.uniform(0, 1, n) < prob).astype(float)
    df = pd.DataFrame({"feature_a": feature_a, "feature_b": feature_b, "label_down_5d": label}, index=dates)
    df.index.name = "as_of"
    return df


def test_walk_forward_evaluate_produces_folds_and_metrics():
    df = _synthetic_df()
    result = walk_forward_evaluate(df, "logistic_regression")
    assert result["folds"] >= 1
    assert result["auc"] is not None
    assert result["auc"] > 0.5  # real, constructed signal
    assert result["feature_names"] == ["feature_a", "feature_b"]


def test_walk_forward_evaluate_insufficient_history_yields_zero_folds():
    df = _synthetic_df(n=100)  # far short of the 5y default window
    result = walk_forward_evaluate(df, "logistic_regression")
    assert result["folds"] == 0
    assert result["auc"] is None


def test_train_and_register_creates_candidate_model(db):
    df = _synthetic_df()
    version = train_and_register(db, df, "logistic_regression", name="test-model")

    assert version.status == "candidate"  # never auto-promoted to active
    assert version.model_type == "logistic_regression"
    assert version.artifact_path
    assert version.metrics["feature_names"] == ["feature_a", "feature_b"]
    assert version.training_window_start < version.training_window_end

    model = load_model(version.artifact_path)
    assert model is not None
    proba = model.predict_proba(np.array([[0.5, -0.5]]))
    assert 0.0 <= proba[0] <= 1.0


def test_train_and_register_rejects_unknown_model_type(db):
    df = _synthetic_df()
    with pytest.raises(ValueError):
        train_and_register(db, df, "not_a_real_model", name="test-model")


def test_train_and_register_rejects_empty_labels(db):
    df = _synthetic_df()
    df["label_down_5d"] = None
    with pytest.raises(ValueError):
        train_and_register(db, df, "logistic_regression", name="test-model")
