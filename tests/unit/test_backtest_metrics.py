import numpy as np
import pytest

from packages.backtesting.metrics import classification_metrics, expected_calibration_error


def test_perfect_predictions_score_well():
    y_true = [0, 0, 1, 1, 0, 1]
    y_prob = [0.01, 0.02, 0.98, 0.95, 0.05, 0.9]
    result = classification_metrics(y_true, y_prob)
    assert result["auc"] == pytest.approx(1.0)
    assert result["brier"] < 0.01
    assert result["n"] == 6


def test_single_class_fold_returns_none_for_undefined_metrics():
    y_true = [0, 0, 0, 0]
    y_prob = [0.1, 0.2, 0.15, 0.05]
    result = classification_metrics(y_true, y_prob)
    assert result["auc"] is None
    assert result["log_loss"] is None
    assert result["brier"] is not None


def test_expected_calibration_error_zero_for_perfectly_calibrated():
    rng = np.random.default_rng(42)
    y_prob = rng.uniform(0, 1, 2000)
    y_true = (rng.uniform(0, 1, 2000) < y_prob).astype(float)
    ece = expected_calibration_error(y_true, y_prob, n_bins=10)
    assert ece < 0.05  # noisy but should be small for a well-calibrated generator


def test_expected_calibration_error_high_for_overconfident_predictions():
    # always predicts near-certain "down" regardless of the (50/50) truth
    y_true = [0, 1, 0, 1, 0, 1, 0, 1]
    y_prob = [0.99] * 8
    ece = expected_calibration_error(y_true, y_prob, n_bins=10)
    assert ece > 0.4
