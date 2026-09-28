import pytest

from packages.signals.scoring import bounded_score, clamp


def test_bounded_score_zero_raw_is_neutral():
    assert bounded_score(0.0, scale=10.0) == pytest.approx(50.0)


def test_bounded_score_positive_raw_pushes_bearish():
    assert bounded_score(50.0, scale=10.0) > 50.0


def test_bounded_score_negative_raw_pushes_bullish():
    assert bounded_score(-50.0, scale=10.0) < 50.0


def test_bounded_score_stays_within_0_100():
    assert 0.0 <= bounded_score(1e6, scale=1.0) <= 100.0
    assert 0.0 <= bounded_score(-1e6, scale=1.0) <= 100.0


def test_clamp_bounds_value():
    assert clamp(150) == 100.0
    assert clamp(-10) == 0.0
    assert clamp(42) == 42.0
