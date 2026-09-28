from datetime import UTC, datetime

from packages.news.dedup import dedup_hash, normalize_headline


def test_normalize_strips_punctuation_and_case():
    assert normalize_headline("Fed Hikes Rates -- Again!") == "fed hikes rates again"


def test_dedup_hash_same_for_republished_headline_same_day():
    a = dedup_hash("Fed hikes rates by 25bp", datetime(2026, 6, 5, 9, 0, tzinfo=UTC))
    b = dedup_hash("FED HIKES RATES BY 25BP", datetime(2026, 6, 5, 23, 0, tzinfo=UTC))
    assert a == b


def test_dedup_hash_differs_for_different_days():
    a = dedup_hash("Fed hikes rates", datetime(2026, 6, 5, tzinfo=UTC))
    b = dedup_hash("Fed hikes rates", datetime(2026, 6, 6, tzinfo=UTC))
    assert a != b


def test_dedup_hash_differs_for_different_headlines():
    a = dedup_hash("Fed hikes rates", datetime(2026, 6, 5, tzinfo=UTC))
    b = dedup_hash("Fed cuts rates", datetime(2026, 6, 5, tzinfo=UTC))
    assert a != b
