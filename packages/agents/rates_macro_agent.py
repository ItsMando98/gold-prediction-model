"""Agent 2 -- Rates & Macro Agent (plan section 50).

Responsibilities: rates, real yields, Fed probabilities, macro releases,
inflation expectations. Fed funds futures / macro releases have no free
public data source wired up yet (see docs/ROADMAP.md) -- this agent
reports that honestly via ``status="unavailable"`` in its data rather than
fabricating a Fed hawkishness score.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from packages.agents.base import AgentResult
from packages.features.data_access import rate_series
from packages.features.indicators import bps_change, last_value

_RATE_LABELS = {"US02Y": "us02y", "US05Y": "us05y", "US10Y": "us10y", "US10Y_REAL": "real_yield_10y"}


def summarize_rates(session: Session, as_of: datetime) -> dict[str, float | None]:
    summary: dict[str, float | None] = {}
    series_by_symbol = {}
    for symbol, label in _RATE_LABELS.items():
        series = rate_series(session, symbol, as_of)
        series_by_symbol[symbol] = series
        summary[f"{label}_level"] = last_value(series)
        summary[f"{label}_change_5d_bps"] = bps_change(series, 5)

    us10y, us02y = series_by_symbol["US10Y"], series_by_symbol["US02Y"]
    if not us10y.empty and not us02y.empty:
        slope = (us10y - us02y).dropna()
        summary["curve_slope_2s10s"] = last_value(slope)
    else:
        summary["curve_slope_2s10s"] = None
    return summary


async def run(session: Session, as_of: datetime) -> AgentResult:
    rates_summary = summarize_rates(session, as_of)
    has_data = any(v is not None for v in rates_summary.values())
    return AgentResult(
        agent="rates_macro",
        status="ok" if has_data else "unavailable",
        detail=(
            "rates summarized"
            if has_data
            else "no rate history available for this as_of"
        )
        + "; Fed funds futures / macro calendar have no free data source configured yet",
        data={"rates": rates_summary, "fed_expectations": None},
    )
