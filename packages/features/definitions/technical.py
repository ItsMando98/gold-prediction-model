"""Technical market-structure features for XAUUSD (plan section 15)."""

from packages.features.context import FeatureContext
from packages.features.indicators import atr, ema, last_value, rsi
from packages.features.registry import register


@register
def technical_xau(ctx: FeatureContext) -> dict[str, float | None]:
    df = ctx.prices.get("XAUUSD")
    keys = [
        "xau_ema_20",
        "xau_ema_50",
        "xau_dist_to_ema20_pct",
        "xau_dist_to_ema50_pct",
        "xau_rsi_14",
        "xau_atr_14",
    ]
    if df is None or df.empty or len(df) < 5:
        return dict.fromkeys(keys)

    close = df["close"]
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    last_close = last_value(close)
    ema20_last = last_value(ema20)
    ema50_last = last_value(ema50)

    return {
        "xau_ema_20": ema20_last,
        "xau_ema_50": ema50_last,
        "xau_dist_to_ema20_pct": (
            (last_close / ema20_last - 1) * 100 if last_close and ema20_last else None
        ),
        "xau_dist_to_ema50_pct": (
            (last_close / ema50_last - 1) * 100 if last_close and ema50_last else None
        ),
        "xau_rsi_14": last_value(rsi(close, 14)),
        "xau_atr_14": last_value(atr(df, 14)),
    }
