"""Baseline ML models (plan sections 24 "Model B", 62).

Each wrapper exposes the same fit/predict_proba(x) -> P(down) contract
(packages.models.base.Model) regardless of the underlying library, so
walk-forward evaluation and the ensemble don't need to know which one is
active.
"""

import lightgbm as lgb
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression


class LogisticRegressionModel:
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("max_iter", 1000)
        self._model = LogisticRegression(**kwargs)

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(x, y)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self._model.predict_proba(x)[:, 1]


class RandomForestModel:
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("n_estimators", 200)
        kwargs.setdefault("max_depth", 5)
        kwargs.setdefault("random_state", 42)
        self._model = RandomForestClassifier(**kwargs)

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(x, y)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self._model.predict_proba(x)[:, 1]


class LightGBMModel:
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("n_estimators", 200)
        kwargs.setdefault("max_depth", 4)
        kwargs.setdefault("random_state", 42)
        kwargs.setdefault("verbosity", -1)
        kwargs.setdefault("min_child_samples", 5)
        self._model = lgb.LGBMClassifier(**kwargs)

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(x, y)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self._model.predict_proba(x)[:, 1]


MODEL_REGISTRY: dict[str, type] = {
    "logistic_regression": LogisticRegressionModel,
    "random_forest": RandomForestModel,
    "lightgbm": LightGBMModel,
}
