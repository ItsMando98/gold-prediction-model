"""Core ORM models (plan section 48, MVP subset).

Only the tables the Phase 0 / Sprint-1 pipeline actually reads or writes
are defined here: market_prices, rates, features, regimes, predictions,
prediction_drivers, provider_health. Later phases (macro_releases,
fed_expectations, cot_positions, etc.) get their own tables and migrations
when that ingestion is actually implemented -- see docs/ROADMAP.md.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.common.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class MarketPrice(Base):
    """OHLCV bar for a tradable instrument (XAUUSD, GC, DXY, Brent, ...)."""

    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint("source", "symbol", "observed_at", "revision", name="uq_market_price"),
        Index("ix_market_prices_symbol_observed_at", "symbol", "observed_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class RateObservation(Base):
    """Single-value observation for rates / yields / spreads (US10Y, real yields, ...)."""

    __tablename__ = "rates"
    __table_args__ = (
        UniqueConstraint("source", "symbol", "observed_at", "revision", name="uq_rate_obs"),
        Index("ix_rates_symbol_observed_at", "symbol", "observed_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class FeatureSnapshot(Base):
    """Versioned, deterministic feature vector for a symbol at a point in time."""

    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint(
            "symbol", "as_of", "feature_set_version", name="uq_feature_snapshot"
        ),
        Index("ix_features_symbol_as_of", "symbol", "as_of"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegimeSnapshot(Base):
    """Classified market regime at a point in time (plan section 21)."""

    __tablename__ = "regimes"
    __table_args__ = (Index("ix_regimes_symbol_as_of", "symbol", "as_of"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    regime: Mapped[str] = mapped_column(String, nullable=False)
    scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Prediction(Base):
    """Immutable prediction object (plan section 27). Never updated in place."""

    __tablename__ = "predictions"
    __table_args__ = (Index("ix_predictions_symbol_created_at", "symbol", "created_at"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    regime: Mapped[str] = mapped_column(String, nullable=False)

    probabilities: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    bias: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    confirmations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    contradictions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    key_levels: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    event_risks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    invalidation: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    model_versions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    feature_snapshot_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("features.id"), nullable=True
    )
    config_version: Mapped[str] = mapped_column(String, nullable=False)
    code_commit: Mapped[str | None] = mapped_column(String, nullable=True)

    drivers: Mapped[list["PredictionDriver"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan"
    )


class PredictionDriver(Base):
    """Per-prediction driver attribution (plan section 41)."""

    __tablename__ = "prediction_drivers"
    __table_args__ = (Index("ix_prediction_drivers_prediction_id", "prediction_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    prediction_id: Mapped[str] = mapped_column(
        String, ForeignKey("predictions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    contribution: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    prediction: Mapped["Prediction"] = relationship(back_populates="drivers")


class ProviderHealth(Base):
    """Health/status ledger for each data provider call (plan section 35 / 80)."""

    __tablename__ = "provider_health"
    __table_args__ = (Index("ix_provider_health_source_symbol_checked_at", "source", "symbol", "checked_at"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # ok | degraded | down
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    message: Mapped[str | None] = mapped_column(String, nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
