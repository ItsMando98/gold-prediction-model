"""OHLCV bar schema for tradable instruments."""

from packages.common.schemas.observation import PointInTimeRecord


class Bar(PointInTimeRecord):
    """A single OHLCV bar. ``observed_at`` is the bar's close/session timestamp."""

    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
