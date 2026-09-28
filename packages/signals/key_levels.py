"""Support/resistance levels from recent price structure (plan section 15)."""

import pandas as pd


def compute_key_levels(xau_prices: pd.DataFrame, lookback_days: int = 20) -> dict[str, list[float]]:
    if xau_prices is None or xau_prices.empty:
        return {"support": [], "resistance": []}

    window = xau_prices.tail(lookback_days)
    week = xau_prices.tail(5)

    levels_low = sorted({round(float(window["low"].min()), 2), round(float(week["low"].min()), 2)})
    levels_high = sorted(
        {round(float(window["high"].max()), 2), round(float(week["high"].max()), 2)}, reverse=True
    )

    return {"support": levels_low, "resistance": levels_high}
