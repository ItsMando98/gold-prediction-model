"""API response models (plan section 27)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionDriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    category: str
    contribution: float
    description: str | None


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    target_time: datetime
    horizon: str
    symbol: str
    regime: str
    probabilities: dict
    risk_score: float
    bias: str
    confidence: float
    confirmations: list[str]
    contradictions: list[str]
    key_levels: dict
    event_risks: list
    invalidation: list[str]
    model_versions: dict
    feature_snapshot_id: str | None
    config_version: str
    code_commit: str | None
    drivers: list[PredictionDriverOut]


class RegimeOut(BaseModel):
    symbol: str
    as_of: datetime
    regime: str
    scores: dict


class ProviderHealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    symbol: str | None
    checked_at: datetime
    status: str
    latency_ms: float | None
    message: str | None
