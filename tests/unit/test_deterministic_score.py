from packages.signals.deterministic import compute_deterministic_score


def test_all_missing_features_gives_neutral_score():
    result = compute_deterministic_score({})
    assert result.risk_score == 50.0
    assert result.data_completeness == 0.0
    assert all(not c.available for c in result.components)


def test_rates_dominated_bearish_scenario_scores_above_neutral():
    features = {
        "real_yield_10y_change_5d_bps": 25.0,
        "us10y_change_5d_bps": 20.0,
        "dxy_return_5d": 0.015,
        "dxy_trend_strength_pct": 1.2,
        "xauusd_return_5d": -0.02,
        "xau_dist_to_ema20_pct": -1.5,
    }
    result = compute_deterministic_score(features)
    assert result.risk_score > 50.0

    rates = next(c for c in result.components if c.name == "rates")
    usd = next(c for c in result.components if c.name == "usd")
    technical = next(c for c in result.components if c.name == "technical")
    assert rates.score > 50.0
    assert usd.score > 50.0
    assert technical.score > 50.0


def test_rates_dominated_bullish_scenario_scores_below_neutral():
    features = {
        "real_yield_10y_change_5d_bps": -25.0,
        "us10y_change_5d_bps": -20.0,
        "dxy_return_5d": -0.015,
        "dxy_trend_strength_pct": -1.2,
        "xauusd_return_5d": 0.02,
        "xau_dist_to_ema20_pct": 1.5,
    }
    result = compute_deterministic_score(features)
    assert result.risk_score < 50.0


def test_oil_component_flips_sign_with_regime():
    inflation_regime = {"wti_return_5d": 0.05, "real_yield_10y_change_5d_bps": 20.0}
    safe_haven_regime = {"wti_return_5d": 0.05, "real_yield_10y_change_5d_bps": -20.0}

    inflation_result = compute_deterministic_score(inflation_regime)
    safe_haven_result = compute_deterministic_score(safe_haven_regime)

    inflation_oil = next(c for c in inflation_result.components if c.name == "oil_inflation")
    safe_haven_oil = next(c for c in safe_haven_result.components if c.name == "oil_inflation")

    # same oil move, opposite direction of effect depending on the prevailing regime
    assert inflation_oil.score > 50.0
    assert safe_haven_oil.score < 50.0


def test_fed_positioning_news_are_neutral_and_unavailable_without_data():
    result = compute_deterministic_score({"xauusd_return_5d": 0.01})
    for name in ("fed", "positioning", "news"):
        component = next(c for c in result.components if c.name == name)
        assert component.available is False
        assert component.score == 50.0
        assert component.contribution == 0.0


def test_data_completeness_reflects_available_components():
    features = {
        "real_yield_10y_change_5d_bps": 5.0,
        "dxy_return_5d": 0.01,
        "xauusd_return_5d": -0.01,
        "wti_return_5d": 0.01,
        "silver_return_5d": -0.02,
    }
    result = compute_deterministic_score(features)
    # rates, usd, technical, oil_inflation, cross_asset available; fed/positioning/news not
    assert result.data_completeness == 5 / 8


def test_positioning_component_bearish_on_crowded_long_liquidation():
    features = {
        "cot_position_zscore_1y": 2.0,
        "xauusd_return_5d": -0.02,
        "cot_weekly_long_change": -3000.0,
        "cot_weekly_short_change": 1500.0,
    }
    result = compute_deterministic_score(features)
    positioning = next(c for c in result.components if c.name == "positioning")
    assert positioning.available is True
    assert positioning.score > 50.0
    assert "liquidation" in positioning.drivers[0] or any("liquidation" in d for d in positioning.drivers)


def test_positioning_component_bullish_on_washed_out_squeeze():
    features = {"cot_position_zscore_1y": -1.8, "xauusd_return_5d": 0.02}
    result = compute_deterministic_score(features)
    positioning = next(c for c in result.components if c.name == "positioning")
    assert positioning.available is True
    assert positioning.score < 50.0


def test_news_component_requires_both_net_score_and_event_count():
    result = compute_deterministic_score({"news_net_score": -0.5})  # no event count
    news = next(c for c in result.components if c.name == "news")
    assert news.available is False

    result = compute_deterministic_score({"news_net_score": 0.5, "news_event_count": 2})
    news = next(c for c in result.components if c.name == "news")
    assert news.available is True
    assert news.score > 50.0
