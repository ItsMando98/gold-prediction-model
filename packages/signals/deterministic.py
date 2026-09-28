"""Deterministic baseline Gold Risk Score (plan sections 26, 60, 73-78).

This is "Model A" -- transparent, debuggable, human-readable, and the
Phase 7 baseline the plan asks to build before any ML model. Every
component score is 0-100 on the same convention as the final score
(section 26): 0 = strongly bullish, 50 = neutral, 100 = strongly bearish.

Positioning (CFTC COT, phase 4) and news (phase 5) are real once data has
been ingested for a given as_of -- otherwise, like Fed expectations (phase
3, still no free data source), they're held at neutral (50, zero tilt)
and flagged ``available=False`` so confidence calculation (section 78)
discounts the prediction instead of silently pretending it's fully
informed.
"""

from dataclasses import dataclass, field

from packages.signals.scoring import bounded_score, clamp

# Weights, plan section 73. Starting assumptions only -- not yet
# statistically validated; see docs/ROADMAP.md for the calibration step
# (plan section 25: "weights must be learned/validated rather than
# permanently hard-coded").
WEIGHTS = {
    "rates": 0.25,
    "usd": 0.15,
    "fed": 0.15,
    "positioning": 0.10,
    "technical": 0.10,
    "news": 0.15,
    "oil_inflation": 0.05,
    "cross_asset": 0.05,
}


@dataclass
class ComponentScore:
    name: str
    weight: float
    score: float  # 0-100, 50 = neutral
    available: bool
    drivers: list[str] = field(default_factory=list)

    @property
    def contribution(self) -> float:
        """Signed contribution to the final score, centered on 0."""
        return self.weight * (self.score - 50.0)


@dataclass
class DeterministicScoreResult:
    risk_score: float  # 0-100, plan section 26
    components: list[ComponentScore]
    data_completeness: float  # fraction of components with real data


def _rates_component(features: dict[str, float | None]) -> ComponentScore:
    real_yield_5d = features.get("real_yield_10y_change_5d_bps")
    us10y_5d = features.get("us10y_change_5d_bps")
    if real_yield_5d is None and us10y_5d is None:
        return ComponentScore("rates", WEIGHTS["rates"], 50.0, available=False)

    raw = (real_yield_5d or 0.0) * 1.0 + (us10y_5d or 0.0) * 0.5
    score = bounded_score(raw, scale=30.0)
    drivers = []
    if real_yield_5d is not None:
        drivers.append(f"US 10Y real yield {real_yield_5d:+.0f}bp/5d")
    if us10y_5d is not None:
        drivers.append(f"US 10Y nominal yield {us10y_5d:+.0f}bp/5d")
    return ComponentScore("rates", WEIGHTS["rates"], score, available=True, drivers=drivers)


def _usd_component(features: dict[str, float | None]) -> ComponentScore:
    dxy_5d = features.get("dxy_return_5d")
    dxy_trend = features.get("dxy_trend_strength_pct")
    if dxy_5d is None:
        return ComponentScore("usd", WEIGHTS["usd"], 50.0, available=False)

    raw = dxy_5d * 1000 + (dxy_trend or 0.0) * 10
    score = bounded_score(raw, scale=25.0)
    drivers = [f"DXY {dxy_5d*100:+.2f}%/5d"]
    if dxy_trend is not None:
        drivers.append(f"DXY {dxy_trend:+.2f}% vs 20d EMA")
    return ComponentScore("usd", WEIGHTS["usd"], score, available=True, drivers=drivers)


def _technical_component(features: dict[str, float | None]) -> ComponentScore:
    xau_5d = features.get("xauusd_return_5d")
    dist_ema20 = features.get("xau_dist_to_ema20_pct")
    if xau_5d is None and dist_ema20 is None:
        return ComponentScore("technical", WEIGHTS["technical"], 50.0, available=False)

    raw = -((xau_5d or 0.0) * 300 + (dist_ema20 or 0.0) * 3)
    score = bounded_score(raw, scale=25.0)
    drivers = []
    if xau_5d is not None:
        drivers.append(f"XAUUSD {xau_5d*100:+.2f}%/5d")
    if dist_ema20 is not None:
        drivers.append(f"XAUUSD {dist_ema20:+.2f}% vs 20d EMA")
    return ComponentScore("technical", WEIGHTS["technical"], score, available=True, drivers=drivers)


def _oil_inflation_component(features: dict[str, float | None]) -> ComponentScore:
    """Plan section 10: oil's effect on gold depends on regime, never a fixed sign."""
    wti_5d = features.get("wti_return_5d")
    real_yield_5d = features.get("real_yield_10y_change_5d_bps")
    if wti_5d is None:
        return ComponentScore("oil_inflation", WEIGHTS["oil_inflation"], 50.0, available=False)

    inflation_regime = (real_yield_5d or 0.0) > 10.0
    raw = wti_5d * 10 if inflation_regime else -wti_5d * 10
    score = bounded_score(raw, scale=1.0)
    channel = "inflation/Fed-hawkish channel" if inflation_regime else "safe-haven/inflation-hedge channel"
    return ComponentScore(
        "oil_inflation",
        WEIGHTS["oil_inflation"],
        score,
        available=True,
        drivers=[f"WTI {wti_5d*100:+.2f}%/5d via {channel}"],
    )


def _cross_asset_component(features: dict[str, float | None]) -> ComponentScore:
    """Plan section 16, limited to the two unambiguous rows (DXY, silver-vs-gold)."""
    dxy_5d = features.get("dxy_return_5d")
    silver_5d = features.get("silver_return_5d")
    xau_5d = features.get("xauusd_return_5d")

    signals: list[float] = []
    drivers: list[str] = []
    if dxy_5d is not None:
        signals.append(1.0 if dxy_5d > 0 else -1.0)
        drivers.append(f"DXY {'rising' if dxy_5d > 0 else 'falling'}")
    if silver_5d is not None and xau_5d is not None:
        underperforming = silver_5d < xau_5d
        signals.append(1.0 if underperforming else -1.0)
        drivers.append(f"silver {'underperforming' if underperforming else 'outperforming'} gold")

    if not signals:
        return ComponentScore("cross_asset", WEIGHTS["cross_asset"], 50.0, available=False)

    score = 50.0 + 50.0 * (sum(signals) / len(signals))
    return ComponentScore(
        "cross_asset", WEIGHTS["cross_asset"], clamp(score), available=True, drivers=drivers
    )


def _positioning_component(features: dict[str, float | None]) -> ComponentScore:
    """Plan section 12: crowding/liquidation-risk from CFTC Managed Money positioning."""
    z1y = features.get("cot_position_zscore_1y")
    if z1y is None:
        return ComponentScore("positioning", WEIGHTS["positioning"], 50.0, available=False)

    raw = z1y * 15.0  # crowded net-long -> bearish tilt; crowded net-short -> bullish tilt
    drivers = [f"COT managed-money net-spec z-score(1y) {z1y:+.2f}"]

    xau_5d = features.get("xauusd_return_5d")
    long_chg = features.get("cot_weekly_long_change")
    short_chg = features.get("cot_weekly_short_change")
    if (
        z1y > 1.0
        and xau_5d is not None
        and xau_5d < 0
        and long_chg is not None
        and short_chg is not None
        and long_chg < 0
        and short_chg > 0
    ):
        raw += 20.0
        drivers.append("gold falling while managed-money longs unwind and shorts build -- liquidation risk")
    elif z1y < -1.0 and xau_5d is not None and xau_5d > 0:
        raw -= 10.0
        drivers.append("washed-out positioning with gold recovering -- short-squeeze potential")

    score = bounded_score(raw, scale=30.0)
    return ComponentScore("positioning", WEIGHTS["positioning"], score, available=True, drivers=drivers)


def _news_component(features: dict[str, float | None]) -> ComponentScore:
    """Plan sections 17-20: aggregated recent News Event Agent output."""
    net_score = features.get("news_net_score")
    event_count = features.get("news_event_count")
    if net_score is None or not event_count:
        return ComponentScore("news", WEIGHTS["news"], 50.0, available=False)

    score = bounded_score(net_score, scale=1.0)
    max_conf = features.get("news_max_confidence")
    drivers = [f"{int(event_count)} recent event(s), peak confidence {max_conf:.2f}" if max_conf else ""]
    return ComponentScore(
        "news", WEIGHTS["news"], score, available=True, drivers=[d for d in drivers if d]
    )


def compute_deterministic_score(features: dict[str, float | None]) -> DeterministicScoreResult:
    components = [
        _rates_component(features),
        _usd_component(features),
        ComponentScore("fed", WEIGHTS["fed"], 50.0, available=False),  # phase 3: no free data source yet
        _positioning_component(features),
        _technical_component(features),
        _news_component(features),
        _oil_inflation_component(features),
        _cross_asset_component(features),
    ]

    risk_score = clamp(50.0 + sum(c.contribution for c in components))
    data_completeness = sum(1 for c in components if c.available) / len(components)

    return DeterministicScoreResult(
        risk_score=risk_score, components=components, data_completeness=data_completeness
    )
