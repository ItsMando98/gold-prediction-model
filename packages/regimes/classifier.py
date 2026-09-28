"""Rule-based regime classifier (plan section 21 & 59, phase 1 of 2).

This is the deliberately simple baseline the plan asks for first
("First: rule-based regime classifier. Then research: HMM / GMM / ML
classifier. Compare performance." -- section 59). Thresholds below are the
plan's own starting assumptions (sections 74/75) and are not yet
statistically validated; docs/ROADMAP.md tracks replacing/calibrating them
once enough history has been backtested.

Positioning- and news-driven regimes (POSITIONING_LIQUIDATION,
POSITIONING_SHORT_SQUEEZE, GOLD_SPECIFIC_FLOW, LIQUIDITY_CRISIS) require
COT/ETF-flow and news data that later phases ingest -- this classifier
never emits them and falls back to MIXED instead of guessing.
"""

from dataclasses import dataclass, field

from packages.regimes.types import Regime

# bps / pct thresholds, plan section 74/75
REAL_YIELD_MOVE_BPS = 10.0
US10Y_MOVE_BPS = 15.0
DXY_MOVE_PCT = 1.0
VIX_ELEVATED = 25.0
VIX_STRESS = 35.0


@dataclass
class RegimeResult:
    regime: Regime
    scores: dict[str, float] = field(default_factory=dict)
    rationale: list[str] = field(default_factory=list)


def classify_regime(features: dict[str, float | None]) -> RegimeResult:
    real_yield_5d = features.get("real_yield_10y_change_5d_bps")
    us10y_5d = features.get("us10y_change_5d_bps")
    dxy_5d = features.get("dxy_return_5d")
    xau_5d = features.get("xauusd_return_5d")
    vix_level = features.get("vix_close_level")
    spx_5d = features.get("spx_return_5d")

    scores = {
        "real_yield_5d_bps": real_yield_5d,
        "us10y_5d_bps": us10y_5d,
        "dxy_5d_pct": (dxy_5d * 100) if dxy_5d is not None else None,
        "xau_5d_pct": (xau_5d * 100) if xau_5d is not None else None,
        "spx_5d_pct": (spx_5d * 100) if spx_5d is not None else None,
    }

    rationale: list[str] = []

    have_rates = real_yield_5d is not None and dxy_5d is not None and xau_5d is not None
    if have_rates:
        rates_bearish = real_yield_5d > REAL_YIELD_MOVE_BPS and xau_5d < 0
        rates_bullish = real_yield_5d < -REAL_YIELD_MOVE_BPS and xau_5d > 0
        dxy_confirms_bearish = dxy_5d * 100 > DXY_MOVE_PCT
        dxy_confirms_bullish = dxy_5d * 100 < -DXY_MOVE_PCT

        if rates_bearish and dxy_confirms_bearish:
            rationale.append(
                f"real yields +{real_yield_5d:.0f}bp/5d, DXY +{dxy_5d*100:.2f}%/5d, "
                f"gold {xau_5d*100:.2f}%/5d"
            )
            return RegimeResult(Regime.RATES_DOMINATED_BEARISH, scores, rationale)

        if rates_bullish and dxy_confirms_bullish:
            rationale.append(
                f"real yields {real_yield_5d:.0f}bp/5d, DXY {dxy_5d*100:.2f}%/5d, "
                f"gold {xau_5d*100:.2f}%/5d"
            )
            return RegimeResult(Regime.RATES_DOMINATED_BULLISH, scores, rationale)

    if dxy_5d is not None and real_yield_5d is not None and abs(real_yield_5d) < REAL_YIELD_MOVE_BPS:
        if dxy_5d * 100 > DXY_MOVE_PCT:
            rationale.append(f"DXY +{dxy_5d*100:.2f}%/5d without a real-yield move")
            return RegimeResult(Regime.USD_DOMINATED, scores, rationale)
        if dxy_5d * 100 < -DXY_MOVE_PCT:
            rationale.append(f"DXY {dxy_5d*100:.2f}%/5d without a real-yield move")
            return RegimeResult(Regime.USD_DOMINATED, scores, rationale)

    if vix_level is not None and xau_5d is not None and spx_5d is not None:
        if vix_level > VIX_ELEVATED and xau_5d > 0 and spx_5d < 0:
            rationale.append(f"VIX {vix_level:.1f}, gold +{xau_5d*100:.2f}%/5d, SPX {spx_5d*100:.2f}%/5d")
            if vix_level > VIX_STRESS:
                return RegimeResult(Regime.LIQUIDITY_CRISIS, scores, rationale)
            return RegimeResult(Regime.SAFE_HAVEN, scores, rationale)
        if spx_5d * 100 < -2.0 and xau_5d < 0:
            rationale.append(f"SPX {spx_5d*100:.2f}%/5d and gold {xau_5d*100:.2f}%/5d falling together")
            return RegimeResult(Regime.RISK_OFF, scores, rationale)
        if spx_5d * 100 > 2.0 and vix_level < VIX_ELEVATED:
            rationale.append(f"SPX +{spx_5d*100:.2f}%/5d, VIX {vix_level:.1f}")
            return RegimeResult(Regime.RISK_ON, scores, rationale)

    rationale.append("no single driver dominates the available signals")
    return RegimeResult(Regime.MIXED, scores, rationale)
