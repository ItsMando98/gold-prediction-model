"""Source credibility tiering (plan section 19).

Tier 3 must never independently generate a high-confidence signal -- that
rule is enforced by ``packages.news.confidence.cap_confidence_for_tier``,
not left to the LLM's discretion.
"""

TIER_1 = {
    "federal reserve",
    "bls",
    "bureau of labor statistics",
    "bea",
    "bureau of economic analysis",
    "us treasury",
    "u.s. treasury",
    "cftc",
    "cme",
    "fred",
    "ecb",
    "boe",
    "bank of england",
    "boj",
    "bank of japan",
    "reuters",
    "bloomberg",
}

TIER_2 = {
    "financial times",
    "wall street journal",
    "wsj",
    "cnbc",
    "world gold council",
    "lbma",
}

# Tier 3 is the default for anything not explicitly listed above
# (specialist newsletters, analyst commentary, social media, X/Twitter,
# Reddit, and any unrecognized source) -- conservative by construction.
MAX_CONFIDENCE_BY_TIER = {1: 1.0, 2: 0.85, 3: 0.55}


def tier_for_source(source: str) -> int:
    normalized = source.strip().lower()
    if normalized in TIER_1:
        return 1
    if normalized in TIER_2:
        return 2
    return 3


def cap_confidence_for_tier(confidence: float, tier: int) -> float:
    """Enforce plan section 19: a lower-tier source can only push confidence so far,
    however confident the model's own read of the text is."""
    return min(confidence, MAX_CONFIDENCE_BY_TIER.get(tier, MAX_CONFIDENCE_BY_TIER[3]))
