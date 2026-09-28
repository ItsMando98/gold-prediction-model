"""CFTC Commitment of Traders record schema (plan section 12)."""

from packages.common.schemas.observation import PointInTimeRecord


class CotRecord(PointInTimeRecord):
    """One weekly Disaggregated COT report row for a symbol.

    ``observed_at`` is the report's `report_date` (the Tuesday the
    positions are as-of); the report itself is published the following
    Friday, which is what ``available_at`` must reflect.
    """

    open_interest: float | None = None
    managed_money_long: float | None = None
    managed_money_short: float | None = None
    producer_long: float | None = None
    producer_short: float | None = None
    swap_dealer_long: float | None = None
    swap_dealer_short: float | None = None
    other_reportable_long: float | None = None
    other_reportable_short: float | None = None
