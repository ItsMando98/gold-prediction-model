"""Provider health ledger (plan sections 35 & 80)."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from packages.common.db.models import ProviderHealth


def record_health(
    session: Session,
    *,
    source: str,
    symbol: str | None,
    status: str,
    latency_ms: float | None = None,
    message: str | None = None,
    extra: dict | None = None,
) -> ProviderHealth:
    """Insert a health record. ``status`` is one of ok | degraded | down."""
    if status not in {"ok", "degraded", "down"}:
        raise ValueError(f"invalid provider health status: {status!r}")

    record = ProviderHealth(
        source=source,
        symbol=symbol,
        checked_at=datetime.now(UTC),
        status=status,
        latency_ms=latency_ms,
        message=message,
        extra=extra or {},
    )
    session.add(record)
    return record
