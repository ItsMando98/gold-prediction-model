"""Point-in-time historical dataset builder (plan section 61, phase 8).

For each ``as_of`` timestamp, computes the full feature vector exactly as
the live pipeline would (``packages.features.engine.compute_features``,
gated by ``available_at <= as_of`` throughout) and pairs it with
forward-looking labels (``packages.backtesting.labels``). No ML work
should begin on a dataset this module produced until
``tests/data_quality`` passes -- plan section 61's own instruction.
"""

from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from packages.backtesting.labels import compute_labels
from packages.features.engine import FEATURE_SET_VERSION, compute_features


def build_dataset(session: Session, symbol: str, dates: list[datetime]) -> pd.DataFrame:
    """One row per ``as_of`` in ``dates``, with feature columns and ``label_*``
    columns. Rows where every label is missing (insufficient forward history,
    e.g. the most recent dates) are kept -- callers doing supervised training
    should drop them explicitly rather than have this function silently do it."""
    rows = []
    for as_of in dates:
        features = compute_features(session, as_of)
        labels = compute_labels(session, symbol, as_of)
        rows.append({"as_of": as_of, "symbol": symbol, **features, **labels})

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.set_index("as_of").sort_index()
    return df


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if not c.startswith("label_") and c != "symbol"]


def dataset_metadata(df: pd.DataFrame) -> dict:
    return {"feature_set_version": FEATURE_SET_VERSION, "n_rows": len(df), "columns": list(df.columns)}
