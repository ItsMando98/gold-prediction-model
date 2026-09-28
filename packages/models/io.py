"""Model artifact persistence.

Local disk under ``infra/models/`` for MVP -- ``docs/ROADMAP.md`` tracks
moving this to real object storage (S3/GCS) before any production use.
"""

from pathlib import Path
from typing import Any

import joblib

_ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "infra" / "models"


def save_model(model: Any, name: str) -> str:
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = _ARTIFACT_DIR / f"{name}.joblib"
    joblib.dump(model, path)
    return str(path)


def load_model(path: str) -> Any | None:
    p = Path(path)
    if not p.exists():
        return None
    return joblib.load(p)
