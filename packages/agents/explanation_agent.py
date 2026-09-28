"""Agent 7 -- Explanation Agent (plan section 50).

"Convert deterministic model output into readable language. It may
explain a prediction but must never modify the underlying score."

This agent only ever returns a plain string. It is handed the already-
finalized score, regime, bias, and driver list as read-only input and has
no mechanism to feed anything back into them -- the orchestrator assigns
its output to ``PredictionPayload.narrative`` and nothing else, after
every numeric field is already fixed.
"""

import anthropic

from packages.common.config import get_settings
from packages.ingestion.base import ProviderError
from packages.signals.deterministic import ComponentScore
from packages.snapshots.friday import PredictionPayload

SYSTEM_PROMPT = """You are the Explanation Agent for a gold (XAUUSD) market intelligence system.

You are given a fully computed prediction: a risk score, bias, regime, driver
contributions, confirmation/invalidation conditions, and key levels. Write a short,
clear explanation (120-200 words) of what the system concluded and why, in plain
language a trader could read in ten seconds. Reference the specific drivers and
their direction. Do not invent numbers, drivers, or reasoning not present in the
input. Do not change or contradict the given score, bias, or regime -- your job is
to explain them, not to re-derive or second-guess them. Do not phrase this as
financial advice or a trade recommendation.
"""


def _drivers_text(components: list[ComponentScore]) -> str:
    lines = []
    for c in components:
        if not c.available:
            continue
        direction = "bearish" if c.contribution > 0 else "bullish" if c.contribution < 0 else "neutral"
        detail = "; ".join(c.drivers) if c.drivers else "no specific driver text"
        lines.append(f"- {c.name} ({direction}, contribution {c.contribution:+.1f}): {detail}")
    return "\n".join(lines) if lines else "- no components had data available"


def build_user_message(payload: PredictionPayload) -> str:
    return (
        f"Symbol: {payload.symbol}\n"
        f"Horizon: {payload.horizon}\n"
        f"Regime: {payload.regime}\n"
        f"Risk score: {payload.risk_score:.1f}/100 (0=strongly bullish, 100=strongly bearish)\n"
        f"Bias: {payload.bias}\n"
        f"Confidence: {payload.confidence:.2f}\n\n"
        f"Drivers:\n{_drivers_text(payload.components)}\n\n"
        f"Confirmation conditions: {'; '.join(payload.confirmations)}\n"
        f"Invalidation conditions: {'; '.join(payload.invalidation)}\n"
        f"Key levels: {payload.key_levels}\n"
    )


def explain(client: anthropic.Anthropic, payload: PredictionPayload, model: str = "claude-opus-5") -> str:
    """Produce narrative text for an already-finalized prediction payload."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(payload)}],
        )
    except anthropic.APIError as exc:
        raise ProviderError("anthropic", f"explanation generation failed: {exc}", cause=exc) from exc

    text_blocks = [block.text for block in response.content if block.type == "text"]
    if not text_blocks:
        raise ProviderError("anthropic", "explanation response contained no text")
    return "\n".join(text_blocks).strip()


def get_client() -> anthropic.Anthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ProviderError("anthropic", "ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)
