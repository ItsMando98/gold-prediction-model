from packages.regimes.types import Regime
from packages.signals.confidence import compute_confidence
from packages.signals.deterministic import ComponentScore


def test_no_available_components_gives_low_confidence():
    components = [ComponentScore("rates", 0.25, 50.0, available=False)]
    assert compute_confidence(components, Regime.MIXED) == 0.1


def test_full_agreement_high_completeness_beats_partial_disagreement():
    agreeing = [
        ComponentScore("rates", 0.25, 80.0, available=True),
        ComponentScore("usd", 0.15, 75.0, available=True),
        ComponentScore("technical", 0.10, 70.0, available=True),
    ]
    disagreeing = [
        ComponentScore("rates", 0.25, 80.0, available=True),
        ComponentScore("usd", 0.15, 20.0, available=True),
        ComponentScore("technical", 0.10, 50.0, available=True),
    ]
    high = compute_confidence(agreeing, Regime.RATES_DOMINATED_BEARISH)
    low = compute_confidence(disagreeing, Regime.MIXED)
    assert high > low


def test_confidence_bounded_0_1():
    components = [ComponentScore("rates", 0.25, 100.0, available=True)]
    value = compute_confidence(components, Regime.RATES_DOMINATED_BEARISH)
    assert 0.0 <= value <= 1.0
