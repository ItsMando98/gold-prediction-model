"""Confirmation / invalidation condition templates (plan section 77).

Generates the explicit "what would prove this wrong" conditions every
prediction must carry, so a bearish call from Friday doesn't quietly stay
"true" once its own drivers have reversed.
"""


def build_confirmation_invalidation(
    bias: str, key_levels: dict[str, list[float]]
) -> tuple[list[str], list[str]]:
    support = key_levels.get("support") or []
    resistance = key_levels.get("resistance") or []

    if bias == "bearish":
        confirmations = [
            f"XAUUSD closes below {support[0]:.0f}" if support else "XAUUSD makes a new swing low",
            "US10Y real yield remains above its 5-day starting level",
            "DXY remains above its 20-day EMA",
        ]
        invalidation = [
            "US real yields reverse lower by more than 10bp",
            "DXY breaks below the prior session's low",
            f"XAUUSD reclaims {resistance[0]:.0f}" if resistance else "XAUUSD reclaims resistance",
        ]
    elif bias == "bullish":
        confirmations = [
            f"XAUUSD closes above {resistance[0]:.0f}" if resistance else "XAUUSD makes a new swing high",
            "US10Y real yield remains below its 5-day starting level",
            "DXY remains below its 20-day EMA",
        ]
        invalidation = [
            "US real yields reverse higher by more than 10bp",
            "DXY breaks above the prior session's high",
            f"XAUUSD breaks {support[0]:.0f}" if support else "XAUUSD breaks support",
        ]
    else:
        confirmations = ["no dominant driver -- treat as low-conviction range"]
        invalidation = ["a single driver (rates, USD, or technical) breaks out decisively"]

    return confirmations, invalidation
