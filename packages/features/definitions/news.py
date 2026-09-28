"""Aggregates recent News Event Agent output into score-ready features
(plan sections 17-20).

Each event's confidence has already been tier-capped (plan section 19,
enforced in packages/news/source_tiers.py) before it reaches here, so
this aggregation doesn't need to know about source tiers itself.
"""

from packages.features.context import FeatureContext
from packages.features.registry import register

_DIRECTION_SIGN = {"gold_down": 1.0, "gold_up": -1.0}  # matches the score convention: higher = more bearish


@register
def news_aggregate(ctx: FeatureContext) -> dict[str, float | None]:
    events = ctx.news
    if not events:
        return {"news_net_score": None, "news_event_count": 0, "news_max_confidence": None}

    weighted_scores: list[float] = []
    confidences: list[float] = []
    for event in events:
        chain = event.get("transmission_chain") or []
        if not chain:
            continue
        sign = _DIRECTION_SIGN.get(chain[-1])
        if sign is None:
            continue
        confidence = event.get("confidence") or 0.0
        relevance = event.get("relevance") or 0.0
        weighted_scores.append(sign * confidence * relevance)
        confidences.append(confidence)

    if not weighted_scores:
        return {"news_net_score": None, "news_event_count": len(events), "news_max_confidence": None}

    return {
        "news_net_score": sum(weighted_scores) / len(weighted_scores),
        "news_event_count": float(len(events)),
        "news_max_confidence": max(confidences),
    }
