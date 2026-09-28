"""Structured event schema the News Event Agent must produce (plan sections 17-20).

This is the contract that keeps an LLM from freely "guessing" a trading
direction (plan section 626): the model must express its read of an
article as a typed, causal transmission chain terminating in an explicit
gold direction, not a bare sentiment label. ``client.messages.parse()``
validates the response against this schema before any of it is trusted.

v1 simplification: section 20 describes multiple *candidate* transmission
chains per event with the regime engine picking which one currently
dominates. Here the agent is given the current regime as context and
asked for its single best-estimate chain under that regime, rather than
enumerating alternatives -- see docs/ROADMAP.md.
"""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class NewsEventCategory(StrEnum):
    """Plan section 18."""

    FEDERAL_RESERVE = "federal_reserve"
    US_INFLATION = "us_inflation"
    US_EMPLOYMENT = "us_employment"
    US_GROWTH = "us_growth"
    TREASURY_MARKET = "treasury_market"
    US_FISCAL_POLICY = "us_fiscal_policy"
    GEOPOLITICS = "geopolitics"
    MIDDLE_EAST = "middle_east"
    OIL_SUPPLY = "oil_supply"
    CENTRAL_BANKS = "central_banks"
    GOLD_PURCHASES = "gold_purchases"
    TRADE_POLICY = "trade_policy"
    SANCTIONS = "sanctions"
    CHINA = "china"
    INDIA = "india"
    ETF_FLOWS = "etf_flows"
    MINING_SUPPLY = "mining_supply"
    FINANCIAL_STRESS = "financial_stress"
    OTHER = "other"


class NewsEvent(BaseModel):
    """One structured, causally-explicit event extracted from an article."""

    event: str = Field(description="Short name for the event, e.g. 'Hormuz escalation'")
    category: NewsEventCategory
    entities: list[str] = Field(description="Named actors/organizations/countries involved")
    direct_assets: list[str] = Field(
        description="Assets the event directly strikes first, e.g. ['Brent', 'WTI']"
    )
    transmission_chain: list[str] = Field(
        description=(
            "Ordered causal steps from the event to gold, e.g. "
            "['oil_up', 'inflation_expectations_up', 'fed_hawkish_repricing', "
            "'real_yields_up', 'gold_down']. Must end in exactly 'gold_up' or 'gold_down'."
        )
    )
    relevance: float = Field(ge=0.0, le=1.0, description="How relevant this event is to gold specifically")
    confidence: float = Field(ge=0.0, le=1.0, description="Model's confidence in this causal read")
    rationale: str = Field(description="One or two sentences explaining the chain")

    @field_validator("transmission_chain")
    @classmethod
    def _must_terminate_in_gold_direction(cls, chain: list[str]) -> list[str]:
        if not chain or chain[-1] not in {"gold_up", "gold_down"}:
            raise ValueError("transmission_chain must end in exactly 'gold_up' or 'gold_down'")
        return chain

    @property
    def gold_direction(self) -> str:
        return self.transmission_chain[-1]
