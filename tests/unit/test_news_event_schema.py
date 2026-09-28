import pytest
from pydantic import ValidationError

from packages.common.schemas import NewsEvent, NewsEventCategory


def _valid_kwargs(**overrides):
    kwargs = dict(
        event="Hormuz escalation",
        category=NewsEventCategory.MIDDLE_EAST,
        entities=["Iran", "United States"],
        direct_assets=["Brent", "WTI"],
        transmission_chain=[
            "oil_up",
            "inflation_expectations_up",
            "fed_hawkish_repricing",
            "real_yields_up",
            "gold_down",
        ],
        relevance=0.7,
        confidence=0.81,
        rationale="Oil supply risk repriced Fed hawkishness higher, pushing real yields up.",
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_event_parses():
    event = NewsEvent(**_valid_kwargs())
    assert event.gold_direction == "gold_down"


def test_transmission_chain_must_end_in_gold_direction():
    with pytest.raises(ValidationError):
        NewsEvent(**_valid_kwargs(transmission_chain=["oil_up", "inflation_expectations_up"]))


def test_transmission_chain_cannot_be_empty():
    with pytest.raises(ValidationError):
        NewsEvent(**_valid_kwargs(transmission_chain=[]))


def test_confidence_and_relevance_bounded_0_1():
    with pytest.raises(ValidationError):
        NewsEvent(**_valid_kwargs(confidence=1.5))
    with pytest.raises(ValidationError):
        NewsEvent(**_valid_kwargs(relevance=-0.1))


def test_gold_up_direction_accepted():
    event = NewsEvent(**_valid_kwargs(transmission_chain=["risk_aversion", "safe_haven_demand", "gold_up"]))
    assert event.gold_direction == "gold_up"
