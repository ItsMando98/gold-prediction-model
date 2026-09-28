import numpy as np
import pandas as pd

from packages.models.ensemble import get_active_model_version, score_with_active_model
from packages.models.train import train_and_register


def _synthetic_df(n=2200, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2015-01-01", periods=n, freq="D")
    feature_a = rng.normal(0, 1, n)
    feature_b = rng.normal(0, 1, n)
    logit = feature_a * 1.5 - feature_b * 0.5
    prob = 1 / (1 + np.exp(-logit))
    label = (rng.uniform(0, 1, n) < prob).astype(float)
    df = pd.DataFrame({"feature_a": feature_a, "feature_b": feature_b, "label_down_5d": label}, index=dates)
    df.index.name = "as_of"
    return df


def test_candidate_model_is_not_active(db):
    train_and_register(db, _synthetic_df(), "logistic_regression", name="candidate-model")
    assert get_active_model_version(db) is None

    score, version = score_with_active_model(db, {"feature_a": 0.5, "feature_b": -0.5})
    assert score is None
    assert version is None


def test_active_model_is_picked_up_and_scores(db):
    version = train_and_register(db, _synthetic_df(), "logistic_regression", name="active-model")
    version.status = "active"
    db.commit()

    active = get_active_model_version(db)
    assert active is not None
    assert active.id == version.id

    # logit = feature_a*1.5 - feature_b*0.5 drives label_down_5d=1 in the synthetic
    # data, so a high positive logit should score a high P(down).
    score, used_version = score_with_active_model(db, {"feature_a": 2.0, "feature_b": -2.0})
    assert score is not None
    assert 0.0 <= score <= 1.0
    assert used_version.id == version.id
    assert score > 0.5


def test_missing_features_are_imputed_not_erroring(db):
    version = train_and_register(db, _synthetic_df(), "logistic_regression", name="active-model-2")
    version.status = "active"
    db.commit()

    score, _ = score_with_active_model(db, {"feature_a": 1.0})  # feature_b missing entirely
    assert score is not None
