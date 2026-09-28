"""Confidence heuristic (plan section 78).

This is a signal-agreement / data-completeness heuristic, not a calibrated
probability of correctness -- plan section 1 is explicit that probability
and confidence values must only become externally visible after proper
historical calibration (section 32), which requires the walk-forward
backtest this MVP does not run yet. Every prediction this module produces
carries ``calibrated=False`` (see packages/snapshots/friday.py) so
downstream consumers cannot mistake this for a validated number.
"""

from packages.regimes.types import Regime
from packages.signals.deterministic import ComponentScore
from packages.signals.scoring import clamp


def compute_confidence(components: list[ComponentScore], regime: Regime) -> float:
    available = [c for c in components if c.available]
    if not available:
        return 0.1

    data_completeness = len(available) / len(components)

    directions = [1 if c.score > 55 else (-1 if c.score < 45 else 0) for c in available]
    nonzero = [d for d in directions if d != 0]
    agreement = abs(sum(nonzero)) / len(nonzero) if nonzero else 0.0

    regime_stability = 1.0 if regime != Regime.MIXED else 0.3

    confidence = 0.35 * data_completeness + 0.45 * agreement + 0.20 * regime_stability
    return clamp(confidence, 0.0, 1.0)
