"""Core ORM models (plan section 48).

Covers Phase 0/Sprint-1 (market_prices, rates, features, regimes,
predictions, prediction_drivers, provider_health) plus Phase 4/5/9
additions (cot_positions, news_articles, news_events, model_versions).
Fed expectations / macro_releases / etf_flows / options_metrics still have
no free public data source wired up -- see docs/ROADMAP.md.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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

    # Populated by the Explanation Agent after the score is finalized (plan section 50,
    # Agent 7) -- read-only narrative, never fed back into risk_score/bias/confidence.
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Raw ML model probability (0-1, "down"), if an active ModelVersion was used;
    # NULL whenever no trained model is registered yet. Distinct from `probabilities`,
    # which stays empty until this is calibrated (plan sections 26 & 32).
    ml_score: Mapped[float | None] = mapped_column(Float, nullable=True)

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


class CotPosition(Base):
    """CFTC Commitment of Traders report, Disaggregated (Managed Money/Producer/Swap
    Dealer) categories for physical commodities (plan section 12)."""

    __tablename__ = "cot_positions"
    __table_args__ = (
        UniqueConstraint("source", "symbol", "observed_at", "revision", name="uq_cot_position"),
        Index("ix_cot_positions_symbol_observed_at", "symbol", "observed_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # report_date
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    open_interest: Mapped[float | None] = mapped_column(Float, nullable=True)
    managed_money_long: Mapped[float | None] = mapped_column(Float, nullable=True)
    managed_money_short: Mapped[float | None] = mapped_column(Float, nullable=True)
    producer_long: Mapped[float | None] = mapped_column(Float, nullable=True)
    producer_short: Mapped[float | None] = mapped_column(Float, nullable=True)
    swap_dealer_long: Mapped[float | None] = mapped_column(Float, nullable=True)
    swap_dealer_short: Mapped[float | None] = mapped_column(Float, nullable=True)
    other_reportable_long: Mapped[float | None] = mapped_column(Float, nullable=True)
    other_reportable_short: Mapped[float | None] = mapped_column(Float, nullable=True)

    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class NewsArticle(Base):
    """Raw news article, stored verbatim before any interpretation (plan section 34)."""

    __tablename__ = "news_articles"
    __table_args__ = (Index("ix_news_articles_published_at", "published_at"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_tier: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 | 2 | 3, plan section 19
    headline: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dedup_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    events: Mapped[list["NewsEventRecord"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class NewsEventRecord(Base):
    """Structured event extracted from a NewsArticle by the News Event Agent
    (plan sections 17-20). ``available_at`` for downstream point-in-time use
    is the article's ``published_at`` -- an event can never be knowable
    before the article that produced it was published."""

    __tablename__ = "news_events"
    __table_args__ = (Index("ix_news_events_article_id", "article_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    article_id: Mapped[str] = mapped_column(String, ForeignKey("news_articles.id"), nullable=False)
    event: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    entities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    direct_assets: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    transmission_chain: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # already tier-capped
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String, nullable=False)  # which LLM/version produced this
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    article: Mapped["NewsArticle"] = relationship(back_populates="events")


class ModelVersion(Base):
    """Registry of trained ML models (plan section 48/81). A model only
    influences live predictions once a row here has status='active' --
    see packages/models/ensemble.py."""

    __tablename__ = "model_versions"
    __table_args__ = (Index("ix_model_versions_status", "status"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    model_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g. logistic_regression, lightgbm
    feature_set_version: Mapped[str] = mapped_column(String, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    training_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    training_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(  # candidate|active|retired
        String, nullable=False, default="candidate"
    )
    artifact_path: Mapped[str | None] = mapped_column(String, nullable=True)
