"""Common model interface every ML baseline implements (plan sections 24/62)."""

from typing import Protocol

import numpy as np


class Model(Protocol):
    def fit(self, x: np.ndarray, y: np.ndarray) -> None: ...

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        """Return P(down) for each row, shape (n_samples,)."""
        ...
