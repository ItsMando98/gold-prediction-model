"""Shared result type for the specialist agents (plan section 50)."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Uniform report every agent returns, so the orchestrator can log/inspect
    them the same way regardless of which agent produced it."""

    agent: str
    status: str  # "ok" | "unavailable" | "error"
    detail: str
    data: dict[str, Any] = field(default_factory=dict)
