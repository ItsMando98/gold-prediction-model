from datetime import UTC, datetime

import pytest

from packages.agents import explanation_agent
from packages.ingestion.base import ProviderError
from packages.signals.deterministic import ComponentScore
from packages.snapshots.friday import PredictionPayload
from tests.anthropic_fakes import FakeCreateClient


def _payload() -> PredictionPayload:
    return PredictionPayload(
        symbol="XAUUSD",
        horizon="weekend_to_monday_close",
        target_time=datetime(2026, 6, 8, 21, 0, tzinfo=UTC),
        regime="RATES_DOMINATED_BEARISH",
        risk_score=72.0,
        bias="bearish",
        confidence=0.7,
        confirmations=["XAUUSD closes below 4235"],
        contradictions=[],
        key_levels={"support": [4235.0], "resistance": [4300.0]},
        invalidation=["real yields reverse lower"],
        model_versions={"calibrated": False},
        feature_snapshot_id="snap-1",
        features={},
        components=[
            ComponentScore("rates", 0.25, 78.0, available=True, drivers=["US 10Y real yield +25bp/5d"]),
            ComponentScore("usd", 0.15, 50.0, available=False),
        ],
    )


def test_explain_returns_model_text_and_does_not_touch_payload():
    client = FakeCreateClient(text="Gold is under pressure as real yields rise...")
    payload = _payload()
    original_score = payload.risk_score

    narrative = explanation_agent.explain(client, payload)

    assert narrative == "Gold is under pressure as real yields rise..."
    assert payload.risk_score == original_score  # explain() never mutates the payload
    assert payload.narrative is None  # caller decides whether/how to assign it


def test_explain_prompt_includes_score_and_drivers():
    client = FakeCreateClient(text="...")
    explanation_agent.explain(client, _payload())

    call = client.messages.calls[0]
    user_content = call["messages"][0]["content"]
    assert "72.0" in user_content
    assert "RATES_DOMINATED_BEARISH" in user_content
    assert "real yield" in user_content


def test_explain_raises_provider_error_on_empty_response():
    class EmptyClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                class Resp:
                    content = []

                return Resp()

    with pytest.raises(ProviderError):
        explanation_agent.explain(EmptyClient(), _payload())
