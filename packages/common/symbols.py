"""Canonical instrument symbols used across the system (plan section 3).

Provider-specific tickers are mapped to these symbols in
``configs/providers/symbols.yaml`` -- application code must never reference
a vendor ticker directly.
"""

from enum import StrEnum


class Symbol(StrEnum):
    XAUUSD = "XAUUSD"
    GC = "GC"  # COMEX gold futures, front month
    DXY = "DXY"
    US02Y = "US02Y"
    US05Y = "US05Y"
    US10Y = "US10Y"
    US10Y_REAL = "US10Y_REAL"
    BRENT = "BRENT"
    WTI = "WTI"
    VIX = "VIX"
    SILVER = "SILVER"
    COPPER = "COPPER"
    SPX = "SPX"
    USDJPY = "USDJPY"
    EURUSD = "EURUSD"


# Symbols an MVP feature/score calculation must have fresh data for.
CORE_SYMBOLS: tuple[Symbol, ...] = (
    Symbol.XAUUSD,
    Symbol.GC,
    Symbol.DXY,
    Symbol.US02Y,
    Symbol.US05Y,
    Symbol.US10Y,
    Symbol.US10Y_REAL,
    Symbol.BRENT,
    Symbol.WTI,
    Symbol.VIX,
    Symbol.SILVER,
    Symbol.COPPER,
    Symbol.SPX,
    Symbol.USDJPY,
    Symbol.EURUSD,
)
