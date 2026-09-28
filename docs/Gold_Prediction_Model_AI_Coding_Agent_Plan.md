# Gold Prediction Model
## AI-Coding-Agent Implementation Plan

**Version:** 1.0  
**Primary market:** XAU/USD / COMEX Gold Futures  
**Primary objective:** Detect and quantify short-term bullish/bearish gold regimes using macro, rates, FX, positioning, volatility, technical, news, and event-risk data.  
**Primary prediction horizon:** Weekend → Monday / 1–5 trading days  
**Secondary horizon:** Intraday and swing extensions after the initial MVP is validated.

---

# 1. Product Goal

Build a continuously running **Gold Prediction Model** that collects market and news data, converts them into structured features, identifies the current macro/market regime, and outputs a probabilistic directional risk assessment for gold.

The system must **not** simply predict:

> "Gold goes down tomorrow."

Instead, it should produce a structured output such as:

```json
{
  "symbol": "XAUUSD",
  "timestamp": "2026-09-27T20:00:00Z",
  "horizon": "next_session",
  "bias": "bearish",
  "downside_risk_score": 82,
  "upside_risk_score": 18,
  "confidence": 0.74,
  "regime": "rates_dominated_bearish",
  "main_drivers": [
    "US 10Y yield rising",
    "DXY strengthening",
    "Fed hike probability increasing",
    "oil shock increasing inflation expectations",
    "speculative positioning remains heavily net-long"
  ],
  "key_levels": {
    "support": [4235, 4200],
    "resistance": [4300, 4350]
  },
  "confirmation": [
    "XAUUSD closes below 4235",
    "US10Y remains above prior-day high",
    "DXY remains above 20-day VWAP"
  ],
  "invalidation": [
    "US real yields reverse lower",
    "DXY breaks intraday support",
    "gold reclaims 4300"
  ]
}
```

Probabilities/confidence values must only become externally visible after proper historical calibration.

---

# 2. Core Design Principles

1. **Probability, not certainty**
2. **Explainable signal stack**
3. **Market regime awareness**
4. **No single-data-source dependency**
5. **No pure LLM trading decisions**
6. **Historical point-in-time correctness**
7. **Backtest before live trust**
8. **Separate raw observations from interpreted signals**
9. **Every prediction must be reproducible**
10. **News and structured market data must be timestamp-aligned**

---

# 3. MVP Scope

The MVP focuses on predicting:

- Friday close → Monday open
- Friday close → Monday close
- Sunday futures reopen → Monday close
- Next 24 hours
- Next 3 trading days

Primary assets:

```text
XAUUSD
GC futures
DXY
US02Y
US05Y
US10Y
US10Y real yield
Brent
WTI
VIX
MOVE
Silver
Copper
S&P 500
USDJPY
EURUSD
```

Later:

```text
Gold miners
GLD
GDX
Treasury futures
SOFR futures
Fed Funds futures
Inflation swaps
ETF flows
Options surfaces
Physical gold premiums
Central-bank purchase data
```

---

# 4. High-Level Architecture

```text
                  ┌─────────────────────┐
                  │   Data Providers    │
                  └──────────┬──────────┘
                             │
             ┌───────────────▼────────────────┐
             │       Ingestion Layer          │
             │ market / macro / news / COT    │
             └───────────────┬────────────────┘
                             │
                    ┌────────▼────────┐
                    │ Raw Data Store  │
                    └────────┬────────┘
                             │
               ┌─────────────▼─────────────┐
               │ Normalization / Alignment │
               └─────────────┬─────────────┘
                             │
                    ┌────────▼────────┐
                    │ Feature Engine  │
                    └────────┬────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │ Regime + Signal + News Intelligence│
          └──────────────────┬──────────────────┘
                             │
                   ┌─────────▼──────────┐
                   │ Prediction Engine  │
                   └─────────┬──────────┘
                             │
             ┌───────────────▼──────────────┐
             │ Calibration / Risk Scoring   │
             └───────────────┬──────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │ API / Dashboard / Alerts / Backtest│
          └─────────────────────────────────────┘
```

---

# 5. Recommended Technology Stack

## Backend

```text
Python 3.12+
FastAPI
Pydantic
SQLAlchemy
Polars
NumPy
SciPy
scikit-learn
LightGBM
XGBoost
statsmodels
PyTorch optional
```

## Data

```text
PostgreSQL
TimescaleDB extension optional
Redis
Parquet
DuckDB for research/backtests
```

## Scheduling / workers

```text
Celery + Redis
or
Temporal
or
APScheduler for MVP
```

Preferred production architecture:

```text
FastAPI + PostgreSQL + TimescaleDB + Redis + Temporal
```

## Frontend

```text
Next.js
TypeScript
Tailwind
shadcn/ui
TradingView Lightweight Charts
TanStack Query
TanStack Table
```

## Infrastructure

```text
Docker
Docker Compose
GitHub Actions
Sentry
Prometheus
Grafana
```

---

# 6. Repository Structure

```text
gold-prediction/
│
├── apps/
│   ├── api/
│   ├── worker/
│   └── dashboard/
│
├── packages/
│   ├── ingestion/
│   ├── normalization/
│   ├── features/
│   ├── regimes/
│   ├── news/
│   ├── signals/
│   ├── models/
│   ├── calibration/
│   ├── backtesting/
│   ├── risk/
│   └── common/
│
├── configs/
│   ├── providers/
│   ├── features/
│   ├── regimes/
│   └── strategies/
│
├── research/
│   ├── notebooks/
│   ├── experiments/
│   └── reports/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── data_quality/
│
├── infra/
│   ├── docker/
│   └── monitoring/
│
└── docs/
```

---

# 7. Data Domains

## 7.1 Gold Market Data

Required:

```text
XAUUSD OHLCV
GC futures OHLCV
GC open interest
GC volume
futures term structure
front-month / next-month spread
```

Derived:

```text
returns
realized volatility
ATR
VWAP
distance to highs/lows
session returns
gap size
overnight return
Friday → Sunday return
Sunday → Monday return
```

---

# 8. Rates Module

Rates are one of the most important gold drivers.

Track:

```text
US 2Y
US 5Y
US 10Y
US 30Y
US 10Y real yield
US 5Y real yield
2s10s
5s30s
Fed Funds expectations
SOFR curve
```

Features:

```text
yield_change_1d
yield_change_5d
yield_zscore_20d
real_yield_momentum
curve_slope_change
rate_volatility
yield_breakout
```

Example interpretation:

```python
if (
    us10y_change_5d > threshold
    and real_yield_change_5d > threshold
    and gold_return_5d < 0
):
    signal = "rates_confirmed_bearish"
```

---

# 9. USD / FX Module

Track:

```text
DXY
USDJPY
EURUSD
GBPUSD
USDCNH
```

Important features:

```text
DXY momentum
DXY breakout
DXY trend strength
DXY/gold inverse correlation
USDJPY carry proxy
USDCNH risk proxy
```

Core hypothesis:

```text
DXY ↑ + real yields ↑ + XAU ↓
=
high-confidence bearish confirmation
```

---

# 10. Inflation / Energy Module

Track:

```text
Brent
WTI
gasoline
natural gas
5Y breakevens
10Y breakevens
5Y5Y inflation expectations
```

Important derived regime:

```text
oil_shock
→ inflation repricing
→ Fed tightening probability
→ yields higher
→ negative gold pressure
```

Do NOT automatically classify higher oil as bullish gold.

The effect depends on regime.

---

# 11. Fed Expectations Module

Track:

```text
current Fed Funds target
next-meeting probability distribution
1-month implied policy expectations
3-month implied expectations
6-month implied expectations
12-month implied expectations
```

Features:

```text
probability_hike_next_meeting
probability_cut_next_meeting
expected_rate_change_3m
expected_rate_change_6m
hawkish_repricing_1d
hawkish_repricing_5d
```

Create:

```text
FED_HAWKISHNESS_SCORE = 0–100
```

---

# 12. CFTC / Positioning Module

Weekly COT data:

```text
Managed Money long
Managed Money short
Producer long
Producer short
Swap Dealer positioning
Open Interest
```

Derived:

```text
net_speculative_position
net_position_pct_open_interest
position_zscore_1y
position_zscore_3y
weekly_long_change
weekly_short_change
crowding_score
liquidation_risk_score
```

Example:

```text
Gold price ↓
+
Managed Money strongly net-long
+
Longs decreasing
+
Shorts increasing
=
elevated long-liquidation risk
```

---

# 13. ETF Flow Module

Track:

```text
GLD holdings
IAU holdings
global gold ETF flows
daily fund inflow/outflow
```

Derived:

```text
flow_1d
flow_5d
flow_20d
flow_momentum
price_flow_divergence
```

Example:

```text
Gold price flat
+
ETF outflows accelerating
=
hidden bearish pressure
```

---

# 14. Options Module

Phase 2 but architect for it from day one.

Track:

```text
ATM implied volatility
25-delta put skew
25-delta call skew
risk reversal
term structure
put/call volume
gamma concentration
major strikes
options expiry dates
```

Important derived signals:

```text
downside_skew
volatility_expansion
dealer_gamma_proxy
large_strike_magnet
tail_risk_pricing
```

---

# 15. Technical Market Structure Module

The technical layer must support, not replace, macro analysis.

Calculate:

```text
20 / 50 / 100 / 200 EMA
VWAP
weekly VWAP
monthly VWAP
ATR
RSI
ADX
Donchian channels
market structure highs/lows
support/resistance
volume profile
breakout / failed breakout
```

Gold-specific levels should support:

```text
major daily swing highs
major daily swing lows
weekly highs/lows
Friday high/low
previous week high/low
round numbers
high-volume nodes
```

---

# 16. Cross-Asset Confirmation Engine

Create an explicit confirmation matrix.

Example:

| Asset | Condition | Interpretation |
|---|---|---|
| XAU | falling | bearish |
| DXY | rising | bearish |
| US10Y | rising | bearish |
| Real yields | rising | strongly bearish |
| Oil | rising | conditional |
| VIX | rising | context dependent |
| Silver | underperforming gold | bearish metals |
| Copper | falling | growth concern |
| S&P | falling | risk-off |

Calculate:

```text
CROSS_ASSET_BEARISH_SCORE
CROSS_ASSET_BULLISH_SCORE
```

---

# 17. News Intelligence System

The news engine must not allow an LLM to freely "guess" direction.

Pipeline:

```text
raw article
→ deduplication
→ entity extraction
→ event classification
→ relevance scoring
→ source credibility
→ time sensitivity
→ affected macro variables
→ expected market transmission
```

Example event:

```json
{
  "event": "Hormuz escalation",
  "entities": ["Iran", "United States"],
  "direct_assets": ["Brent", "WTI"],
  "transmission_chain": [
    "oil_up",
    "inflation_expectations_up",
    "fed_hawkish_repricing",
    "real_yields_up",
    "gold_down"
  ],
  "confidence": 0.81
}
```

---

# 18. News Categories

```text
Federal Reserve
US inflation
US employment
US growth
Treasury market
US fiscal policy
geopolitics
Middle East
oil supply
central banks
gold purchases
trade policy
sanctions
China
India
ETF flows
mining supply
financial stress
```

---

# 19. News Source Hierarchy

Tier 1:

```text
Federal Reserve
BLS
BEA
US Treasury
CFTC
CME
FRED
ECB
BoE
BoJ
Reuters
Bloomberg
```

Tier 2:

```text
Financial Times
Wall Street Journal
CNBC
major bank research
World Gold Council
LBMA
```

Tier 3:

```text
specialist newsletters
analyst commentary
social media
X / Twitter
Reddit
```

Tier 3 must never independently generate a high-confidence signal.

---

# 20. Event Knowledge Graph

Represent causal relationships explicitly.

Example graph:

```text
Hormuz disruption
    ↓
Oil supply risk
    ↓
Brent ↑
    ↓
Inflation expectation ↑
    ↓
Fed hike probability ↑
    ↓
US yields ↑
    ↓
USD ↑
    ↓
Gold ↓
```

Alternative possible path:

```text
Geopolitical shock
    ↓
Risk aversion
    ↓
Safe-haven demand
    ↓
Gold ↑
```

The regime engine decides which transmission channel currently dominates.

---

# 21. Regime Engine

This is one of the core components.

Possible regimes:

```text
RATES_DOMINATED_BEARISH
RATES_DOMINATED_BULLISH
USD_DOMINATED
INFLATION_HEDGE
SAFE_HAVEN
LIQUIDITY_CRISIS
RISK_ON
RISK_OFF
GOLD_SPECIFIC_FLOW
POSITIONING_LIQUIDATION
POSITIONING_SHORT_SQUEEZE
MIXED
```

Example rules:

```python
if real_yields_trend > 0 and dxy_trend > 0 and xau_trend < 0:
    regime = "RATES_DOMINATED_BEARISH"
```

Later replace static rules with a regime classifier.

Candidate algorithms:

```text
Hidden Markov Model
Gaussian Mixture Model
K-Means
Bayesian regime-switching
LightGBM classifier
```

---

# 22. Feature Store

Feature format:

```json
{
  "timestamp": "...",
  "symbol": "XAUUSD",
  "feature_set_version": "v1",
  "features": {
    "xau_return_1d": -0.012,
    "dxy_return_5d": 0.018,
    "us10y_change_5d_bps": 24,
    "real_yield_change_5d_bps": 18,
    "fed_hawkishness": 78,
    "cot_crowding": 84,
    "news_bearish_score": 71
  }
}
```

Every feature must have:

```text
name
description
source
timestamp
calculation
lookback
version
```

---

# 23. Prediction Targets

Never train on one target only.

Create multiple labels.

## Direction

```text
next_session_return > 0
next_session_return < 0
```

## Significant move

```text
return <= -0.5%
return <= -1.0%
return <= -2.0%

return >= +0.5%
return >= +1.0%
return >= +2.0%
```

## Volatility

```text
next_session_absolute_return
next_session_high_low_range
gap_size
```

## Weekend-specific

```text
Friday close → Sunday futures open
Friday close → Monday open
Friday close → Monday close
Sunday open → Monday close
```

---

# 24. Model Architecture

Use an ensemble.

## Model A — Deterministic Signal Engine

Purpose:

```text
transparent
debuggable
human-readable
```

---

## Model B — Gradient Boosting

Recommended:

```text
LightGBM
```

Inputs:

```text
market features
macro features
positioning
event scores
technical features
regime
```

---

## Model C — Time-Series Model

Optional after MVP:

```text
Temporal Fusion Transformer
LSTM
N-BEATS
Transformer encoder
```

Only keep if it outperforms simpler models out-of-sample.

---

## Model D — News/Event Model

LLM/classifier produces structured event features.

It must NOT directly execute trades.

---

# 25. Ensemble

Example:

```text
Final Score =
0.25 deterministic macro signal
+ 0.30 LightGBM probability
+ 0.15 positioning model
+ 0.15 news/event model
+ 0.15 technical confirmation
```

Weights must be learned/validated rather than permanently hard-coded.

---

# 26. Gold Risk Score

Output:

```text
0–20   strongly bullish
21–40  moderately bullish
41–59  neutral/mixed
60–79  moderately bearish
80–100 strongly bearish
```

Internal implementation should calculate independent probabilities first.

Do not derive fake probabilities directly from the score.

---

# 27. Prediction Object

```json
{
  "prediction_id": "uuid",
  "created_at": "...",
  "target_time": "...",
  "horizon": "weekend_to_monday",
  "symbol": "XAUUSD",
  "regime": "RATES_DOMINATED_BEARISH",

  "probabilities": {
    "down": 0.74,
    "up": 0.26,
    "down_gt_1pct": 0.42,
    "up_gt_1pct": 0.13
  },

  "risk_score": 82,

  "drivers": [],
  "confirmations": [],
  "contradictions": [],
  "key_levels": [],
  "event_risks": [],
  "invalidation": [],

  "model_versions": {},
  "feature_snapshot_id": "uuid"
}
```

---

# 28. Backtesting Requirements

The backtest must be **point-in-time correct**.

Forbidden:

```text
future COT values
future revised macro values
articles published after prediction timestamp
future technical levels
look-ahead adjusted futures data
```

---

# 29. Walk-Forward Backtesting

Use:

```text
train
→ validation
→ forward test
→ roll window
→ repeat
```

Example:

```text
2012–2018 train
2019 validation
2020 test

2013–2019 train
2020 validation
2021 test
...
```

Do not use random train/test splits for time-series predictions.

---

# 30. Weekend Backtest

Build a dedicated test dataset containing every tradable weekend.

For each Friday snapshot:

```text
market state at Friday close
latest available COT
latest macro data
Fed expectations
news up to Friday timestamp
```

Then create additional snapshots:

```text
Saturday 12:00
Saturday 23:59
Sunday 12:00
Sunday pre-open
Sunday futures open
```

Measure how probabilities evolve after new information arrives.

---

# 31. Key Backtest Metrics

Classification:

```text
accuracy
balanced accuracy
precision
recall
F1
ROC-AUC
PR-AUC
Brier Score
log loss
```

Calibration:

```text
calibration curve
Expected Calibration Error
Brier Score
```

Trading relevance:

```text
average forward return per score bucket
Sharpe ratio
Sortino ratio
max drawdown
profit factor
hit rate
expected value
```

---

# 32. Probability Calibration

Raw ML probabilities must be calibrated.

Use:

```text
Platt scaling
Isotonic regression
Beta calibration
```

Example validation:

Predictions labeled 70% bearish should historically produce bearish outcomes approximately 70% of the time.

---

# 33. Leakage Protection

Create automated leakage tests.

Examples:

```text
feature_timestamp <= prediction_timestamp
article_published_at <= prediction_timestamp
macro_release_time <= prediction_timestamp
COT_publish_time <= prediction_timestamp
```

Test failure must stop the backtest.

---

# 34. News Backtest Archive

A major challenge is historical news.

Store raw articles immediately from day one:

```text
headline
body
source
published_at
received_at
entities
classification
sentiment
event_type
```

For historical research use reputable archived feeds where licensing permits.

---

# 35. Data Quality Layer

Every provider receives a health score.

Monitor:

```text
missing data
stale values
timestamp anomalies
price spikes
duplicate articles
broken feeds
schema changes
```

Prediction engine must downgrade confidence when important feeds are unavailable.

---

# 36. Weekend Intelligence Workflow

Every Friday after market close:

```text
1. freeze Friday market snapshot
2. calculate macro regime
3. calculate positioning risk
4. identify critical technical levels
5. identify scheduled Monday events
6. generate base weekend forecast
```

Saturday/Sunday:

```text
1. ingest new geopolitical/macro news
2. identify material events
3. map events to causal graph
4. estimate changed macro variables
5. recalculate regime
6. recalculate prediction
7. compare against Friday baseline
```

Output:

```text
FRIDAY_BASELINE
SATURDAY_UPDATE
SUNDAY_UPDATE
PRE_OPEN_UPDATE
```

---

# 37. Prediction Delta

The system should explain what changed.

Example:

```json
{
  "previous_score": 65,
  "current_score": 82,
  "delta": 17,
  "reasons": [
    "Iran/Hormuz negotiations deteriorated",
    "Brent futures risk repriced higher",
    "Fed hike probability increased"
  ]
}
```

This is essential.

---

# 38. Scheduled Macro Calendar

Track:

```text
CPI
PCE
NFP
unemployment
wages
ISM
GDP
retail sales
Fed meetings
Fed speeches
Treasury auctions
central-bank meetings
options expiries
```

Generate:

```text
EVENT_RISK_SCORE
```

---

# 39. Surprise Engine

For macro releases:

```text
SURPRISE =
actual - consensus
```

Normalize using historical surprise distributions.

Then estimate impact:

```text
CPI upside surprise
→ rates
→ USD
→ gold
```

---

# 40. Correlation Regime Detection

Rolling correlations:

```text
XAU vs DXY
XAU vs US10Y
XAU vs real yields
XAU vs Brent
XAU vs VIX
XAU vs S&P
```

Use:

```text
20d
60d
120d
```

Purpose:

Avoid assuming historical relationships remain stable.

---

# 41. Driver Attribution

Each prediction must produce contribution estimates.

Example:

```text
Real yields:        -24
DXY:                -18
Fed repricing:      -15
Positioning:        -11
Oil shock:           -9
Safe-haven demand:   +8
Technical support:   -6
------------------------
Net score:           82 bearish
```

Use SHAP for ML models.

---

# 42. Scenario Engine

Generate at least three scenarios.

Example:

```text
Scenario A — Rates continue higher
Probability: calibrated
Expected impact: bearish

Scenario B — Geopolitical escalation dominates safe-haven flows
Expected impact: bullish

Scenario C — Yields reverse lower
Expected impact: bullish recovery
```

Do not force probabilities before calibration.

---

# 43. API Endpoints

```text
GET /prediction/current
GET /prediction/history
GET /prediction/{id}

GET /regime/current
GET /signals/current
GET /drivers/current

GET /market/xau
GET /market/rates
GET /market/fx

GET /news/events
GET /calendar/upcoming

GET /backtest/results
GET /model/health
GET /data/health
```

---

# 44. Dashboard

Main screen:

```text
Gold Prediction Score
Current regime
Bullish probability
Bearish probability
Prediction horizon
Confidence
```

Secondary panels:

```text
Main drivers
Contradicting signals
Rates
DXY
Fed expectations
Oil
Positioning
News
Technical levels
Upcoming events
```

---

# 45. Weekend Dashboard

Dedicated screen:

```text
Friday Base Forecast
↓
Saturday Changes
↓
Sunday Changes
↓
Pre-Open Forecast
↓
Actual Monday Outcome
```

Include:

```text
prediction delta chart
news catalyst timeline
rates/oil/DXY expectations
critical price levels
```

---

# 46. Alert System

Alerts only on meaningful changes.

Examples:

```text
Gold bearish score > 80
Prediction changes by > 15 points
Regime changes
Critical support breaks
DXY + yields confirm simultaneously
Major geopolitical catalyst detected
Fed probability changes > X percentage points
```

---

# 47. Model Monitoring

Monitor:

```text
prediction accuracy
probability calibration
feature drift
regime performance
provider failures
model drift
```

Performance should be broken down by regime.

Example:

```text
RATES_DOMINATED_BEARISH
SAFE_HAVEN
LIQUIDITY_CRISIS
```

---

# 48. Database Tables

Core:

```text
market_prices
rates
macro_releases
fed_expectations
cot_positions
etf_flows
options_metrics
news_articles
news_events
features
regimes
predictions
prediction_drivers
prediction_updates
backtest_runs
model_versions
provider_health
```

---

# 49. Minimum Data Schema

Every observation:

```text
id
source
symbol
observed_at
available_at
ingested_at
value
revision
metadata
```

`available_at` is mandatory for point-in-time backtesting.

---

# 50. Agent Architecture

Suggested specialist agents:

## Agent 1 — Market Data Agent

Responsibilities:

```text
collect
normalize
validate
store
```

---

## Agent 2 — Rates & Macro Agent

```text
rates
real yields
Fed probabilities
macro releases
inflation expectations
```

---

## Agent 3 — Positioning Agent

```text
COT
ETF flows
options
open interest
```

---

## Agent 4 — News Event Agent

```text
news ingestion
event extraction
deduplication
causal mapping
```

---

## Agent 5 — Regime Agent

```text
classify regime
detect regime changes
```

---

## Agent 6 — Prediction Agent

```text
assemble features
execute models
create forecast
```

---

## Agent 7 — Explanation Agent

Convert deterministic model output into readable language.

It may explain a prediction but must never modify the underlying score.

---

## Agent 8 — Backtest Agent

```text
walk-forward validation
performance reports
calibration tests
regression tests
```

---

# 51. AI Coding Agent Rules

Every coding agent must:

```text
read existing interfaces before modifying code
avoid duplicating business logic
create tests for every calculation
preserve point-in-time timestamps
use typed schemas
never silently swallow provider errors
never generate synthetic production market data
```

Every PR must include:

```text
implementation
tests
migration if required
configuration
documentation
```

---

# 52. Agent Task Format

Every implementation task should follow:

```markdown
## Objective

## Context

## Inputs

## Required Outputs

## Constraints

## Interfaces

## Edge Cases

## Tests

## Definition of Done
```

---

# 53. Implementation Phases

## Phase 0 — Foundation

Build:

```text
monorepo
Docker environment
PostgreSQL
TimescaleDB optional
Redis
FastAPI
worker
Next.js dashboard
CI
logging
```

Definition of Done:

```text
docker compose up
starts entire stack
health endpoint succeeds
database migrations work
```

---

# 54. Phase 1 — Core Market Data

Implement:

```text
XAUUSD
GC
DXY
US2Y
US5Y
US10Y
real yields
Brent
WTI
VIX
```

Build normalization and timestamps.

Definition of Done:

```text
historical import
live polling
automatic retries
data quality checks
```

---

# 55. Phase 2 — Feature Engine

Implement:

```text
returns
momentum
volatility
yield changes
DXY momentum
cross-asset confirmation
technical levels
```

All features must be deterministic and versioned.

---

# 56. Phase 3 — Macro / Fed Engine

Implement:

```text
Fed expectations
macro calendar
macro surprise
inflation expectations
Fed hawkishness score
```

---

# 57. Phase 4 — Positioning

Implement:

```text
CFTC COT
open interest
crowding
liquidation risk
ETF flows
```

---

# 58. Phase 5 — News Intelligence

Implement:

```text
news ingestion
deduplication
entity extraction
event taxonomy
relevance
causal chains
```

LLM output must conform to Pydantic schema.

---

# 59. Phase 6 — Regime Engine

First:

```text
rule-based regime classifier
```

Then research:

```text
HMM
GMM
ML classifier
```

Compare performance.

---

# 60. Phase 7 — Deterministic Prediction Engine

Create first risk score without ML.

Example:

```text
rates score
USD score
Fed score
positioning score
technical score
news score
```

This becomes the baseline model.

---

# 61. Phase 8 — Historical Dataset

Create a point-in-time dataset containing:

```text
daily feature snapshots
Friday snapshots
weekend snapshots
labels
regime
```

No ML work should begin until dataset integrity tests pass.

---

# 62. Phase 9 — ML Baseline

Train:

```text
logistic regression
random forest
LightGBM
XGBoost
```

Compare:

```text
AUC
Brier
calibration
expected trading return
```

---

# 63. Phase 10 — Ensemble

Combine:

```text
deterministic
LightGBM
news
positioning
regime
```

Use validation to optimize weights.

---

# 64. Phase 11 — Weekend Prediction Engine

Create:

```text
Friday baseline
Saturday update
Sunday update
pre-open prediction
```

Track score deltas.

This is the primary product feature.

---

# 65. Phase 12 — Dashboard

Build pages:

```text
/overview
/weekend
/drivers
/news
/rates
/positioning
/backtest
/models
/system
```

---

# 66. Phase 13 — Alerts

Implement:

```text
email
Telegram
Discord
webhook
push notifications
```

Alerts should explain:

```text
what changed
why it matters
current score
previous score
critical level
```

---

# 67. Phase 14 — Paper Trading

Before live capital:

Run for at least:

```text
8–12 weeks
```

Store:

```text
prediction timestamp
available data
signal
market outcome
model version
```

No retroactive edits.

---

# 68. Phase 15 — Trading Strategy Layer

Only after signal validation.

Possible rule:

```text
enter only if:
bearish probability > calibrated threshold
AND
cross-asset confirmation
AND
technical confirmation
```

Risk controls:

```text
max risk per trade
max daily loss
max weekly loss
volatility-adjusted sizing
event blackout rules
```

---

# 69. Research Questions

Research independently:

```text
Do real yields lead gold returns?
How stable is DXY inverse correlation?
Does COT crowding improve tail prediction?
Do weekend geopolitical events create exploitable Monday gaps?
Does oil improve prediction during inflation regimes?
Does FedWatch repricing lead or follow gold?
Which technical breaks create nonlinear liquidation?
```

---

# 70. Ablation Testing

For each signal family remove it and retest.

Example:

```text
model without COT
model without news
model without rates
model without technicals
```

Purpose:

Determine whether every module contributes real predictive value.

---

# 71. Feature Importance

Use:

```text
SHAP
permutation importance
gain importance
```

Measure by regime.

A feature may be important in one regime and useless in another.

---

# 72. Avoid These Mistakes

Do not:

```text
train on revised macro values
use publication-date-incorrect news
random split time series
overfit technical indicators
assume gold always rises during war
use LLM sentiment as sole predictor
convert arbitrary score directly into probability
optimize only win rate
ignore transaction costs
ignore overnight gaps
ignore futures rollover
```

---

# 73. Initial Deterministic Score Example

Start with an explicit baseline.

```text
Rates                25%
Dollar               15%
Fed expectations     15%
Positioning           10%
Technical             10%
News/events           15%
Oil/inflation          5%
Cross-asset            5%
```

These weights are starting assumptions only.

They must later be validated.

---

# 74. Initial Bearish Conditions

Example:

```text
US10Y 5d change > +15bp
real yield 5d change > +10bp
DXY > 20d EMA
DXY 5d return > 1%
Gold below 20d EMA
Gold breaks prior-week low
Fed hike probability rising
COT net-long > 80th percentile
oil shock > threshold
```

---

# 75. Initial Bullish Conditions

Example:

```text
real yields falling
DXY weakening
Fed easing repricing
ETF inflows
gold breaks resistance
safe-haven regime detected
spec positioning washed out
```

---

# 76. Weekend Risk Algorithm

Pseudo-code:

```python
snapshot = load_friday_snapshot()

score = base_model(snapshot)

for event in weekend_events:

    event_signal = classify_event(event)

    causal_effects = map_event_to_market_variables(
        event_signal,
        regime=snapshot.regime
    )

    score = update_prediction(
        previous_score=score,
        causal_effects=causal_effects
    )

return score
```

---

# 77. Invalidation Logic

Every prediction requires explicit invalidation.

Example:

```text
Bearish prediction invalidated if:

US10Y falls > 10bp
AND
DXY breaks previous-day low
AND
XAU reclaims broken support
```

This prevents stale predictions.

---

# 78. Confidence Calculation

Confidence depends on:

```text
model agreement
signal agreement
regime stability
data completeness
historical calibration
news certainty
```

Example:

```text
high score + conflicting models
≠
high confidence
```

---

# 79. Data Provider Abstraction

Create common interfaces.

```python
class MarketDataProvider:
    async def get_quote(...)
    async def get_history(...)
```

Never couple business logic directly to a vendor SDK.

This allows switching providers later.

---

# 80. Provider Failover

Example:

```text
Primary XAU feed
→ secondary feed
→ tertiary feed
```

Store:

```text
source
latency
quality
confidence
```

---

# 81. Reproducibility

Every prediction stores:

```text
model hash
feature set version
raw snapshot IDs
config version
code commit
```

It must be possible to rerun any historical prediction exactly.

---

# 82. Testing Strategy

Unit tests:

```text
feature calculations
score calculations
timestamp rules
regime rules
```

Integration tests:

```text
provider → database
database → feature engine
feature → model
model → API
```

Regression tests:

```text
known historical market episodes
```

---

# 83. Historical Test Cases

Add explicit replay tests for:

```text
COVID crash
2022 inflation/rate shock
Ukraine invasion
major Fed pivots
banking crisis
Middle East escalations
large gold breakouts
large gold liquidations
```

Purpose:

Ensure the regime engine behaves logically.

---

# 84. Observability

Log:

```text
prediction generated
regime changed
provider failed
feature missing
news catalyst added
model disagreement
```

Metrics:

```text
ingestion delay
prediction latency
data completeness
model confidence
calibration error
```

---

# 85. Security

```text
secrets in environment/secret manager
provider keys encrypted
RBAC dashboard
audit log
rate limiting
no secrets in frontend
```

---

# 86. MVP Definition of Done

MVP is complete when:

- Historical gold/rates/USD/oil data is stored.
- Feature engine is deterministic.
- Friday snapshots can be reproduced historically.
- COT positioning is integrated.
- Macro/Fed signals are integrated.
- News events are converted into structured events.
- Rule-based regime detection works.
- A deterministic gold risk score exists.
- Walk-forward backtest is implemented.
- Probabilities are calibrated.
- Weekend forecast updates can be generated.
- Prediction deltas are explainable.
- Dashboard shows current forecast and drivers.
- Every prediction is stored immutably.

---

# 87. First AI Coding Agent Sprint

Execute in this order.

## Task 1

Create monorepo and local Docker environment.

## Task 2

Define canonical timestamped observation schema.

## Task 3

Implement PostgreSQL migrations.

## Task 4

Create provider abstraction.

## Task 5

Integrate XAUUSD / GC historical prices.

## Task 6

Integrate DXY and US Treasury rates.

## Task 7

Build feature-engine framework.

## Task 8

Implement initial rates/USD/gold features.

## Task 9

Create Friday snapshot generator.

## Task 10

Create deterministic baseline score.

## Task 11

Build historical prediction storage.

## Task 12

Create basic `/prediction/current` API.

---

# 88. First Milestone

The first usable milestone should answer:

> Based only on information that was actually available at Friday's close, how bearish or bullish was gold for the next Monday session, and why?

The system must then show:

```text
prediction
regime
drivers
contradictions
critical levels
actual result
```

This milestone should be completed before adding complex deep-learning models.

---

# 89. Final Product Vision

The final application becomes a continuously running **Gold Market Intelligence & Prediction System**.

It should combine:

```text
macro economics
rates
FX
oil
positioning
options
technical structure
news
geopolitical events
event risk
machine learning
```

into one explainable forecast.

The system's main competitive advantage should not be:

> "AI predicts gold."

It should be:

> **The platform continuously reconstructs the current gold market regime, identifies what is actually driving price, measures whether those drivers are strengthening or weakening, and updates an empirically calibrated probability distribution before the market fully reprices new information.**
