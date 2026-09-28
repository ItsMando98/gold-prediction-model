"""Loads the canonical-symbol -> vendor-ticker mapping from configs/providers/symbols.yaml."""

from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "providers" / "symbols.yaml"


@lru_cache
def _load() -> dict[str, dict[str, str]]:
    with _CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh)


def get_ticker(provider: str, symbol: str) -> str | None:
    return _load().get(provider, {}).get(symbol)


def supported_symbols(provider: str) -> set[str]:
    return set(_load().get(provider, {}).keys())
