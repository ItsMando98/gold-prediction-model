"""DXY momentum and cross-asset confirmation inputs (plan sections 9 & 16)."""

from packages.features.context import FeatureContext
from packages.features.indicators import ema, last_value, pct_return, rolling_correlation
from packages.features.registry import register


@register
def cross_asset(ctx: FeatureContext) -> dict[str, float | None]:
    out: dict[str, float | None] = {}

    dxy = ctx.prices.get("DXY")
    if dxy is not None and not dxy.empty:
        out["dxy_momentum_5d"] = pct_return(dxy["close"], 5)
        ema20 = ema(dxy["close"], 20)
        ema20_last = last_value(ema20)
        last_close = last_value(dxy["close"])
        out["dxy_trend_strength_pct"] = (
            (last_close / ema20_last - 1) * 100 if last_close and ema20_last else None
        )
    else:
        out["dxy_momentum_5d"] = None
        out["dxy_trend_strength_pct"] = None

    xau = ctx.prices.get("XAUUSD")
    if xau is not None and not xau.empty and dxy is not None and not dxy.empty:
        out["xau_dxy_corr_20d"] = rolling_correlation(xau["close"], dxy["close"], 20)
    else:
        out["xau_dxy_corr_20d"] = None

    us10y = ctx.rates.get("US10Y")
    if xau is not None and not xau.empty and us10y is not None and not us10y.empty:
        out["xau_us10y_corr_20d"] = rolling_correlation(xau["close"], us10y, 20)
    else:
        out["xau_us10y_corr_20d"] = None

    return out
