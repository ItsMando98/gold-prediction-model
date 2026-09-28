"""Classification & calibration metrics (plan section 31)."""

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score


def classification_metrics(y_true, y_prob) -> dict[str, float | int | None]:
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)

    if len(np.unique(y_true)) < 2:
        # AUC/PR-AUC/log-loss are undefined with a single class present in this fold.
        return {
            "auc": None,
            "pr_auc": None,
            "brier": float(brier_score_loss(y_true, y_prob)),
            "log_loss": None,
            "n": int(len(y_true)),
        }

    return {
        "auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "brier": float(brier_score_loss(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob, labels=[0, 1])),
        "n": int(len(y_true)),
    }


def expected_calibration_error(y_true, y_prob, n_bins: int = 10) -> float:
    """Mean absolute gap between predicted probability and observed frequency,
    binned into ``n_bins`` equal-width buckets (plan section 32/31)."""
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)

    ece = 0.0
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_prob >= lo) & (y_prob <= hi if i == n_bins - 1 else y_prob < hi)
        if not mask.any():
            continue
        bin_accuracy = float(y_true[mask].mean())
        bin_confidence = float(y_prob[mask].mean())
        ece += (mask.sum() / len(y_prob)) * abs(bin_accuracy - bin_confidence)
    return float(ece)
