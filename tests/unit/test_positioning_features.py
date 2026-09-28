import pandas as pd

from packages.features.context import FeatureContext
from packages.features.definitions.positioning import cot_positioning


def _ctx_with_cot(df: pd.DataFrame) -> FeatureContext:
    from datetime import UTC, datetime

    return FeatureContext(as_of=datetime(2026, 6, 5, tzinfo=UTC), cot={"GC": df})


def test_missing_cot_data_returns_all_none():
    result = cot_positioning(_ctx_with_cot(pd.DataFrame()))
    assert all(v is None for v in result.values())


def test_computes_net_position_and_changes():
    df = pd.DataFrame(
        {
            "managed_money_long": [190_000.0, 195_000.0, 200_000.0],
            "managed_money_short": [45_000.0, 42_000.0, 40_000.0],
            "open_interest": [480_000.0, 490_000.0, 500_000.0],
        }
    )
    result = cot_positioning(_ctx_with_cot(df))

    assert result["cot_net_speculative_position"] == 160_000.0
    assert result["cot_net_position_pct_oi"] == (160_000.0 / 500_000.0) * 100
    assert result["cot_weekly_long_change"] == 5_000.0
    assert result["cot_weekly_short_change"] == -2_000.0
    assert result["cot_open_interest"] == 500_000.0
    # not enough weekly history for a 52-report z-score
    assert result["cot_position_zscore_1y"] is None


def test_zscore_computed_with_enough_history():
    n = 60
    df = pd.DataFrame(
        {
            "managed_money_long": [150_000.0 + i * 500 for i in range(n)],
            "managed_money_short": [50_000.0 for _ in range(n)],
            "open_interest": [450_000.0 for _ in range(n)],
        }
    )
    result = cot_positioning(_ctx_with_cot(df))
    assert result["cot_position_zscore_1y"] is not None
    # net position is monotonically increasing -> the latest value is the max -> positive z-score
    assert result["cot_position_zscore_1y"] > 0
