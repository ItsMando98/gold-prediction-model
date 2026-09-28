"""Rates module features (plan section 8)."""

from packages.features.context import FeatureContext
from packages.features.indicators import bps_change, last_value
from packages.features.registry import register

_LABELS = {"US02Y": "us02y", "US05Y": "us05y", "US10Y": "us10y", "US10Y_REAL": "real_yield_10y"}


@register
def rate_changes(ctx: FeatureContext) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for symbol, label in _LABELS.items():
        series = ctx.rates.get(symbol)
        out[f"{label}_level"] = last_value(series) if series is not None else None
        out[f"{label}_change_1d_bps"] = bps_change(series, 1) if series is not None else None
        out[f"{label}_change_5d_bps"] = bps_change(series, 5) if series is not None else None

    us10y = ctx.rates.get("US10Y")
    us02y = ctx.rates.get("US02Y")
    if us10y is not None and us02y is not None and not us10y.empty and not us02y.empty:
        slope = (us10y - us02y).dropna()
        out["curve_slope_2s10s"] = last_value(slope)
        out["curve_slope_2s10s_change_5d_bps"] = bps_change(slope, 5)
    else:
        out["curve_slope_2s10s"] = None
        out["curve_slope_2s10s_change_5d_bps"] = None
    return out
