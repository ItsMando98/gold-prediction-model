"""Versioned feature registry.

Every feature definition module registers its compute function here via
``@register``. Bump ``FEATURE_SET_VERSION`` whenever a feature's
calculation changes meaning -- persisted snapshots are keyed by version so
historical predictions stay reproducible (plan section 81) even as the
feature set evolves.
"""

from collections.abc import Callable

from packages.features.context import FeatureContext

FEATURE_SET_VERSION = "v1"

FeatureFn = Callable[[FeatureContext], dict[str, float | None]]

_REGISTRY: list[FeatureFn] = []


def register(fn: FeatureFn) -> FeatureFn:
    _REGISTRY.append(fn)
    return fn


def compute_all(ctx: FeatureContext) -> dict[str, float | None]:
    features: dict[str, float | None] = {}
    for fn in _REGISTRY:
        features.update(fn(ctx))
    return features
