import pandas as pd
import pytest

from packages.features.indicators import (
    atr,
    bps_change,
    ema,
    last_value,
    pct_return,
    rolling_correlation,
    rsi,
)


def test_pct_return_basic():
    series = pd.Series([100.0, 101.0, 102.0, 100.0, 98.0, 105.0])
    assert pct_return(series, 1) == pytest.approx(105.0 / 98.0 - 1)
    assert pct_return(series, 5) == pytest.approx(105.0 / 100.0 - 1)


def test_pct_return_insufficient_history_returns_none():
    series = pd.Series([100.0, 101.0])
    assert pct_return(series, 5) is None


def test_bps_change_converts_percentage_points_to_bps():
    series = pd.Series([4.00, 4.05, 4.10, 4.20, 4.15, 4.25])
    # last (4.25) vs 1 back (4.15) = +0.10pp = +10bps
    assert bps_change(series, 1) == pytest.approx(10.0)
    # last (4.25) vs 5 back (4.00) = +0.25pp = +25bps
    assert bps_change(series, 5) == pytest.approx(25.0)


def test_ema_last_value_between_min_and_max():
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = ema(series, 3)
    assert series.min() < result.iloc[-1] < series.max()


def test_rsi_all_gains_is_100():
    series = pd.Series([float(i) for i in range(1, 20)])  # strictly increasing
    result = rsi(series, 14)
    assert last_value(result) == pytest.approx(100.0)


def test_rsi_all_losses_is_0():
    series = pd.Series([float(i) for i in range(20, 1, -1)])  # strictly decreasing
    result = rsi(series, 14)
    assert last_value(result) == pytest.approx(0.0)


def test_atr_requires_ohlc_columns():
    df = pd.DataFrame(
        {
            "open": [10, 11, 12, 11, 10, 12, 13],
            "high": [11, 12, 13, 12, 11, 13, 14],
            "low": [9, 10, 11, 10, 9, 11, 12],
            "close": [10.5, 11.5, 12.5, 11.5, 10.5, 12.5, 13.5],
        }
    )
    result = atr(df, period=3)
    assert last_value(result) > 0


def test_rolling_correlation_perfectly_correlated_series():
    # Same per-step growth rate -> identical pct-change series -> correlation of exactly 1.0.
    a = pd.Series([100.0 * (1.01**i) for i in range(30)])
    b = pd.Series([50.0 * (1.01**i) for i in range(30)])
    corr = rolling_correlation(a, b, window=20)
    assert corr == pytest.approx(1.0, abs=1e-9)


def test_rolling_correlation_insufficient_history_returns_none():
    a = pd.Series([1.0, 2.0, 3.0])
    b = pd.Series([1.0, 2.0, 3.0])
    assert rolling_correlation(a, b, window=20) is None


def test_last_value_empty_series_returns_none():
    assert last_value(pd.Series(dtype=float)) is None
