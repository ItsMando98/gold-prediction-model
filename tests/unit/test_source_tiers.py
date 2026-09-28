from packages.news.source_tiers import cap_confidence_for_tier, tier_for_source


def test_tier1_sources():
    assert tier_for_source("Reuters") == 1
    assert tier_for_source("BLOOMBERG") == 1
    assert tier_for_source("Federal Reserve") == 1


def test_tier2_sources():
    assert tier_for_source("Wall Street Journal") == 2
    assert tier_for_source("cnbc") == 2


def test_unknown_source_defaults_to_tier3():
    assert tier_for_source("Random Substack Newsletter") == 3
    assert tier_for_source("X (Twitter)") == 3


def test_cap_confidence_never_exceeds_tier_ceiling():
    assert cap_confidence_for_tier(0.99, tier=3) == 0.55
    assert cap_confidence_for_tier(0.40, tier=3) == 0.40  # below cap, unchanged
    assert cap_confidence_for_tier(0.99, tier=1) == 0.99
    assert cap_confidence_for_tier(0.95, tier=2) == 0.85
