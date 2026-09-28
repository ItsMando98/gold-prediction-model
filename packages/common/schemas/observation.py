"""Canonical timestamped observation schemas.

Every raw value the system ingests -- a price bar, a yield, a COT figure,
a macro release -- must be represented through one of these schemas before
it is persisted. ``available_at`` is the single point-in-time contract the
rest of the system (features, snapshots, backtests) relies on: it is the
timestamp that may legally be compared against a prediction's
``created_at`` when deciding whether the observation was actually knowable
at that moment. Using ``observed_at`` for that comparison is a leakage bug.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PointInTimeRecord(BaseModel):
    """Shared point-in-time fields (plan section 49)."""

    model_config = ConfigDict(frozen=True)

    id: str | None = Field(default=None, description="Assigned by the store on insert")
    source: str
    symbol: str
    observed_at: datetime
    available_at: datetime
    ingested_at: datetime
    revision: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_ordering(self) -> "PointInTimeRecord":
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        if self.ingested_at < self.available_at:
            raise ValueError("ingested_at cannot precede available_at")
        return self


class Observation(PointInTimeRecord):
    """A single scalar observation, e.g. a yield, index level, or macro print."""

    value: float
