"""Return / momentum features for every tracked price instrument (plan section 7.1)."""

from packages.features.context import PRICE_SYMBOLS, FeatureContext
from packages.features.indicators import last_value, pct_return
from packages.features.registry import register


@register
def price_returns(ctx: FeatureContext) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for symbol in PRICE_SYMBOLS:
        df = ctx.prices.get(symbol)
        key = symbol.lower()
        if df is None or df.empty:
            out[f"{key}_return_1d"] = None
            out[f"{key}_return_5d"] = None
            out[f"{key}_close_level"] = None
            continue
        out[f"{key}_return_1d"] = pct_return(df["close"], 1)
        out[f"{key}_return_5d"] = pct_return(df["close"], 5)
        out[f"{key}_close_level"] = last_value(df["close"])
    return out
