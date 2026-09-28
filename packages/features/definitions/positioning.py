"""CFTC COT positioning features (plan section 12)."""

import pandas as pd

from packages.features.context import FeatureContext
from packages.features.indicators import last_value
from packages.features.registry import register


def _zscore(series: pd.Series, window: int) -> float | None:
    series = series.dropna()
    if len(series) < window:
        return None
    window_slice = series.tail(window)
    std = window_slice.std()
    if not std or pd.isna(std):
        return None
    return float((window_slice.iloc[-1] - window_slice.mean()) / std)


@register
def cot_positioning(ctx: FeatureContext) -> dict[str, float | None]:
    keys = [
        "cot_net_speculative_position",
        "cot_net_position_pct_oi",
        "cot_position_zscore_1y",
        "cot_position_zscore_3y",
        "cot_weekly_long_change",
        "cot_weekly_short_change",
        "cot_open_interest",
    ]
    df = ctx.cot.get("GC")
    if df is None or df.empty or "managed_money_long" not in df or df["managed_money_long"].isna().all():
        return dict.fromkeys(keys)

    net_spec = (df["managed_money_long"] - df["managed_money_short"]).dropna()
    if net_spec.empty:
        return dict.fromkeys(keys)

    oi = df["open_interest"].reindex(net_spec.index)
    net_pct_oi = (net_spec / oi.replace(0, float("nan"))) * 100

    long_series = df["managed_money_long"].dropna()
    short_series = df["managed_money_short"].dropna()
    weekly_long_change = (
        float(long_series.iloc[-1] - long_series.iloc[-2]) if len(long_series) >= 2 else None
    )
    weekly_short_change = (
        float(short_series.iloc[-1] - short_series.iloc[-2]) if len(short_series) >= 2 else None
    )

    return {
        "cot_net_speculative_position": last_value(net_spec),
        "cot_net_position_pct_oi": last_value(net_pct_oi),
        # ~52 weekly reports/year, ~156 for 3y
        "cot_position_zscore_1y": _zscore(net_spec, window=52),
        "cot_position_zscore_3y": _zscore(net_spec, window=156),
        "cot_weekly_long_change": weekly_long_change,
        "cot_weekly_short_change": weekly_short_change,
        "cot_open_interest": last_value(df["open_interest"]),
    }
