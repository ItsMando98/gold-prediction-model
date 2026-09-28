import numpy as np
import pytest

from packages.models.baseline import MODEL_REGISTRY


def _toy_data(n=200, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, size=(n, 3))
    logit = x[:, 0] * 2.0 - x[:, 1] * 1.0
    prob = 1 / (1 + np.exp(-logit))
    y = (rng.uniform(0, 1, n) < prob).astype(float)
    return x, y


@pytest.mark.parametrize("model_type", list(MODEL_REGISTRY.keys()))
def test_model_fits_and_predicts_probabilities(model_type):
    x, y = _toy_data()
    model = MODEL_REGISTRY[model_type]()
    model.fit(x, y)
    proba = model.predict_proba(x)

    assert proba.shape == (len(y),)
    assert np.all((proba >= 0.0) & (proba <= 1.0))


@pytest.mark.parametrize("model_type", list(MODEL_REGISTRY.keys()))
def test_model_learns_the_signal(model_type):
    x, y = _toy_data(n=500)
    model = MODEL_REGISTRY[model_type]()
    model.fit(x, y)
    proba = model.predict_proba(x)

    from sklearn.metrics import roc_auc_score

    auc = roc_auc_score(y, proba)
    assert auc > 0.6  # meaningfully better than random on a constructed signal
