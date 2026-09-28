from packages.regimes.classifier import classify_regime
from packages.regimes.types import Regime


def test_rates_dominated_bearish():
    features = {
        "real_yield_10y_change_5d_bps": 15.0,
        "dxy_return_5d": 0.015,
        "xauusd_return_5d": -0.02,
    }
    result = classify_regime(features)
    assert result.regime == Regime.RATES_DOMINATED_BEARISH


def test_rates_dominated_bullish():
    features = {
        "real_yield_10y_change_5d_bps": -15.0,
        "dxy_return_5d": -0.015,
        "xauusd_return_5d": 0.02,
    }
    result = classify_regime(features)
    assert result.regime == Regime.RATES_DOMINATED_BULLISH


def test_usd_dominated_when_rates_quiet():
    features = {
        "real_yield_10y_change_5d_bps": 2.0,
        "dxy_return_5d": 0.02,
        "xauusd_return_5d": -0.01,
    }
    result = classify_regime(features)
    assert result.regime == Regime.USD_DOMINATED


def test_safe_haven_regime():
    features = {
        "vix_close_level": 28.0,
        "xauusd_return_5d": 0.03,
        "spx_return_5d": -0.02,
    }
    result = classify_regime(features)
    assert result.regime == Regime.SAFE_HAVEN


def test_liquidity_crisis_regime():
    features = {
        "vix_close_level": 40.0,
        "xauusd_return_5d": 0.03,
        "spx_return_5d": -0.05,
    }
    result = classify_regime(features)
    assert result.regime == Regime.LIQUIDITY_CRISIS


def test_risk_off_regime():
    features = {
        "vix_close_level": 18.0,
        "spx_return_5d": -0.035,
        "xauusd_return_5d": -0.015,
    }
    result = classify_regime(features)
    assert result.regime == Regime.RISK_OFF


def test_risk_on_regime():
    features = {
        "vix_close_level": 14.0,
        "spx_return_5d": 0.03,
        "xauusd_return_5d": 0.0,
    }
    result = classify_regime(features)
    assert result.regime == Regime.RISK_ON


def test_missing_data_falls_back_to_mixed():
    result = classify_regime({})
    assert result.regime == Regime.MIXED


def test_never_emits_positioning_or_news_regimes_without_that_data():
    # No combination of price/rates-only features should ever produce a regime
    # that plan section 21 defines as requiring COT/ETF/news data.
    unsupported = {
        Regime.POSITIONING_LIQUIDATION,
        Regime.POSITIONING_SHORT_SQUEEZE,
        Regime.GOLD_SPECIFIC_FLOW,
        Regime.INFLATION_HEDGE,
    }
    scenarios = [
        {"real_yield_10y_change_5d_bps": v, "dxy_return_5d": d, "xauusd_return_5d": x}
        for v in (-30, -10, 0, 10, 30)
        for d in (-0.03, 0.0, 0.03)
        for x in (-0.03, 0.0, 0.03)
    ]
    for features in scenarios:
        assert classify_regime(features).regime not in unsupported
