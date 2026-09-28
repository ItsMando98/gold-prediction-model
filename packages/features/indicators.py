"""Pure, deterministic indicator calculations shared by feature definitions.

No I/O here -- everything operates on already-fetched pandas Series/
DataFrames so it can be unit tested without a database.
"""

import pandas as pd


def pct_return(series: pd.Series, n: int) -> float | None:
    """Percent return over the last ``n`` observations, or None if insufficient history."""
    series = series.dropna()
    if len(series) <= n:
        return None
    return float(series.iloc[-1] / series.iloc[-1 - n] - 1)


def bps_change(series: pd.Series, n: int) -> float | None:
    """Change over the last ``n`` observations of a percentage-point series, in basis points."""
    series = series.dropna()
    if len(series) <= n:
        return None
    return float((series.iloc[-1] - series.iloc[-1 - n]) * 100)


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.dropna().ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    series = series.dropna()
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))
    result = 100 - (100 / (1 + rs))
    # avg_loss == 0: no losses in the window -> RSI is 100 (or 50 if also flat, no gains either).
    no_losses = avg_loss == 0
    result = result.where(~no_losses, 100.0)
    result = result.where(~(no_losses & (avg_gain == 0)), 50.0)
    return result


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range. ``df`` must have high/low/close columns."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.rolling(period).mean()


def last_value(series: pd.Series) -> float | None:
    series = series.dropna()
    if series.empty:
        return None
    return float(series.iloc[-1])


def rolling_correlation(a: pd.Series, b: pd.Series, window: int) -> float | None:
    merged = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(merged) < window:
        return None
    corr = merged["a"].pct_change().tail(window).corr(merged["b"].pct_change().tail(window))
    return float(corr) if pd.notna(corr) else None
