"""Walk-forward split generator (plan section 29).

Chronological rolling windows only -- never a random train/test split for
time-series data (plan section 72's explicit "do not" list).
"""

from collections.abc import Iterator
from dataclasses import dataclass

import pandas as pd


@dataclass
class WalkForwardSplit:
    train_index: pd.DatetimeIndex
    validation_index: pd.DatetimeIndex
    test_index: pd.DatetimeIndex


def walk_forward_splits(
    dates: pd.DatetimeIndex,
    train_years: float,
    validation_years: float,
    test_years: float,
    step_years: float | None = None,
) -> Iterator[WalkForwardSplit]:
    """Yield rolling (train, validation, test) windows over ``dates``, each
    strictly later than the previous one. ``step_years`` defaults to
    ``test_years`` (non-overlapping test windows), matching plan section 29's
    "train -> validation -> forward test -> roll window -> repeat"."""
    if dates.empty:
        return

    step_years = step_years or test_years
    dates = dates.sort_values()
    start, end = dates.min(), dates.max()

    train_delta = pd.Timedelta(days=round(train_years * 365))
    val_delta = pd.Timedelta(days=round(validation_years * 365))
    test_delta = pd.Timedelta(days=round(test_years * 365))
    step_delta = pd.Timedelta(days=round(step_years * 365))
    if step_delta <= pd.Timedelta(0):
        raise ValueError("step_years must be positive")

    window_start = start
    while True:
        train_end = window_start + train_delta
        val_end = train_end + val_delta
        test_end = val_end + test_delta
        if test_end > end:
            break

        train_index = dates[(dates >= window_start) & (dates < train_end)]
        val_index = dates[(dates >= train_end) & (dates < val_end)]
        test_index = dates[(dates >= val_end) & (dates < test_end)]

        if len(train_index) and len(val_index) and len(test_index):
            yield WalkForwardSplit(train_index, val_index, test_index)

        window_start += step_delta
