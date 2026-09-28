"""Forward-looking prediction targets (plan section 23).

Every label here is computed from ``full_price_history`` -- the one place
allowed to look forward from ``as_of`` (that's the definition of a label).
Never reuse this module inside a feature definition.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from packages.features.data_access import full_price_history

_SIGNIFICANT_MOVE_PCT = 0.01  # 1%, plan section 23
_HORIZONS_DAYS = (1, 5)

LABEL_NAMES: tuple[str, ...] = (
    "label_return_1d",
    "label_down_1d",
    "label_return_5d",
    "label_down_5d",
    "label_down_gt_1pct_5d",
    "label_up_gt_1pct_5d",
)


def compute_labels(session: Session, symbol: str, as_of: datetime) -> dict[str, float | None]:
    """Forward return/direction labels anchored at the last known close at/before
    ``as_of``. Returns all-None if there isn't enough surrounding history."""
    window = full_price_history(session, symbol, as_of - timedelta(days=5), as_of + timedelta(days=14))
    empty = dict.fromkeys(LABEL_NAMES)
    if window.empty:
        return empty

    anchor_candidates = window[window.index <= as_of]
    future_candidates = window[window.index > as_of]
    if anchor_candidates.empty or future_candidates.empty:
        return empty

    anchor_close = float(anchor_candidates["close"].iloc[-1])
    labels: dict[str, float | None] = dict(empty)

    for horizon in _HORIZONS_DAYS:
        if len(future_candidates) < horizon:
            continue
        forward_close = float(future_candidates["close"].iloc[horizon - 1])
        ret = forward_close / anchor_close - 1.0
        labels[f"label_return_{horizon}d"] = ret
        labels[f"label_down_{horizon}d"] = 1.0 if ret < 0 else 0.0
        if horizon == 5:
            labels["label_down_gt_1pct_5d"] = 1.0 if ret <= -_SIGNIFICANT_MOVE_PCT else 0.0
            labels["label_up_gt_1pct_5d"] = 1.0 if ret >= _SIGNIFICANT_MOVE_PCT else 0.0

    return labels
