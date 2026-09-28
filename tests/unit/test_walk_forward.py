import pandas as pd

from packages.backtesting.walk_forward import walk_forward_splits


def test_empty_dates_yields_nothing():
    assert list(walk_forward_splits(pd.DatetimeIndex([]), 1, 1, 1)) == []


def test_splits_are_chronological_and_non_overlapping():
    dates = pd.date_range("2015-01-01", "2023-12-31", freq="D")
    splits = list(walk_forward_splits(dates, train_years=3, validation_years=1, test_years=1))

    assert len(splits) >= 2
    for split in splits:
        assert split.train_index.max() < split.validation_index.min()
        assert split.validation_index.max() < split.test_index.min()

    # each successive split starts later than the previous one (rolls forward)
    for a, b in zip(splits, splits[1:], strict=False):
        assert a.train_index.min() < b.train_index.min()


def test_insufficient_history_yields_no_splits():
    dates = pd.date_range("2024-01-01", "2024-03-01", freq="D")
    splits = list(walk_forward_splits(dates, train_years=3, validation_years=1, test_years=1))
    assert splits == []


def test_step_years_defaults_to_test_years():
    dates = pd.date_range("2015-01-01", "2020-12-31", freq="D")
    splits = list(walk_forward_splits(dates, train_years=2, validation_years=0.5, test_years=1))
    assert len(splits) >= 1
    if len(splits) >= 2:
        gap = splits[1].train_index.min() - splits[0].train_index.min()
        assert gap == pd.Timedelta(days=365)
