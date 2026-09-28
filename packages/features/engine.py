"""Builds and persists a versioned feature snapshot for a symbol/timestamp."""

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from packages.common.db.models import FeatureSnapshot
from packages.features import definitions  # noqa: F401  -- registers all feature fns
from packages.features.context import build_context
from packages.features.registry import FEATURE_SET_VERSION, compute_all


def compute_features(session: Session, as_of: datetime) -> dict[str, float | None]:
    ctx = build_context(session, as_of)
    return compute_all(ctx)


def generate_snapshot(session: Session, symbol: str, as_of: datetime) -> FeatureSnapshot:
    """Compute and persist a feature snapshot, idempotent on (symbol, as_of, version)."""
    features = compute_features(session, as_of)

    stmt = pg_insert(FeatureSnapshot).values(
        symbol=symbol,
        as_of=as_of,
        feature_set_version=FEATURE_SET_VERSION,
        features=features,
        created_at=datetime.now(UTC),
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_feature_snapshot",
        set_={"features": stmt.excluded.features, "created_at": stmt.excluded.created_at},
    ).returning(FeatureSnapshot.id)
    result = session.execute(stmt)
    snapshot_id = result.scalar_one()
    session.commit()
    return session.get(FeatureSnapshot, snapshot_id)
