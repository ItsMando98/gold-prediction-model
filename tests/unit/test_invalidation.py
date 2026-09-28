from packages.signals.invalidation import build_confirmation_invalidation


def test_bearish_confirmation_references_support_and_resistance():
    confirmations, invalidation = build_confirmation_invalidation(
        "bearish", {"support": [4235.0, 4200.0], "resistance": [4300.0, 4350.0]}
    )
    assert any("4235" in c for c in confirmations)
    assert any("4300" in i for i in invalidation)


def test_bullish_confirmation_references_support_and_resistance():
    confirmations, invalidation = build_confirmation_invalidation(
        "bullish", {"support": [4235.0, 4200.0], "resistance": [4300.0, 4350.0]}
    )
    assert any("4300" in c for c in confirmations)
    assert any("4235" in i for i in invalidation)


def test_neutral_bias_has_generic_conditions():
    empty_levels = {"support": [], "resistance": []}
    confirmations, invalidation = build_confirmation_invalidation("neutral", empty_levels)
    assert confirmations and invalidation


def test_handles_missing_levels_gracefully():
    empty_levels = {"support": [], "resistance": []}
    confirmations, invalidation = build_confirmation_invalidation("bearish", empty_levels)
    assert confirmations and invalidation
