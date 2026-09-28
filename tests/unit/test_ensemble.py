from packages.models.ensemble import build_feature_vector, combine


def test_combine_falls_back_to_deterministic_without_ml():
    assert combine(70.0, None) == 70.0


def test_combine_blends_towards_ml_probability():
    # ML says 90% down-probability (score 90), deterministic says 60 -> blend moves up
    result = combine(60.0, 0.9, weight_ml=0.5)
    assert result == (60.0 + 90.0) / 2


def test_combine_weight_zero_ignores_ml():
    assert combine(55.0, 0.1, weight_ml=0.0) == 55.0


def test_build_feature_vector_imputes_missing_as_zero():
    vec = build_feature_vector({"a": 1.0, "b": None}, ["a", "b", "c"])
    assert vec.tolist() == [[1.0, 0.0, 0.0]]
