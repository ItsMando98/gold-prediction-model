import pandas as pd

from packages.signals.key_levels import compute_key_levels


def test_empty_dataframe_returns_empty_levels():
    result = compute_key_levels(pd.DataFrame())
    assert result == {"support": [], "resistance": []}


def test_computes_support_and_resistance_from_recent_range():
    df = pd.DataFrame(
        {
            "open": [100, 102, 98, 105, 103, 101, 99, 104],
            "high": [101, 103, 99, 106, 104, 102, 100, 105],
            "low": [99, 101, 97, 104, 102, 100, 98, 103],
            "close": [100.5, 102.5, 98.5, 105.5, 103.5, 101.5, 99.5, 104.5],
        }
    )
    result = compute_key_levels(df, lookback_days=8)
    assert result["support"] == sorted(result["support"])
    assert result["resistance"] == sorted(result["resistance"], reverse=True)
    assert min(result["support"]) == 97.0
    assert max(result["resistance"]) == 106.0
