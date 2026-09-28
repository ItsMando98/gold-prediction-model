"""Provider abstraction (plan section 79).

Business logic must never import a vendor SDK or call a vendor endpoint
directly -- it depends only on these interfaces, so providers can be
swapped or added to a failover chain (plan section 80) without touching
callers.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from packages.common.schemas import Bar, Observation


class ProviderError(RuntimeError):
    """Raised when a provider fails to return usable data."""

    def __init__(self, provider: str, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider = provider
        self.cause = cause


class PriceProvider(ABC):
    """Source of OHLCV bars for tradable instruments (XAUUSD, GC, DXY, ...)."""

    name: str

    @abstractmethod
    async def get_history(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        """Return bars covering ``[start, end]``, oldest first."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> Bar:
        """Return the latest available bar for ``symbol``."""

    @abstractmethod
    def supports(self, symbol: str) -> bool:
        """Whether this provider has a ticker mapping for ``symbol``."""


class RateProvider(ABC):
    """Source of scalar time series (yields, spreads, macro prints)."""

    name: str

    @abstractmethod
    async def get_history(self, symbol: str, start: datetime, end: datetime) -> list[Observation]:
        """Return observations covering ``[start, end]``, oldest first."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> Observation:
        """Return the latest available observation for ``symbol``."""

    @abstractmethod
    def supports(self, symbol: str) -> bool:
        """Whether this provider has a series mapping for ``symbol``."""
