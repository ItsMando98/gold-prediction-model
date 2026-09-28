# Roadmap: plan sections vs. what's implemented

Full plan: `docs/Gold_Prediction_Model_AI_Coding_Agent_Plan.md`. This tracks
status against it so nobody has to diff the whole document to find out
what's real.

## Done: Phase 0 + First Sprint (plan sections 53-54 & 87, Tasks 1-12)

| Plan section | Status |
|---|---|
| §6 Repository structure | done (`apps/`, `packages/`, `configs/`, `research/`, `tests/`, `infra/`, `docs/`) |
| §49 Point-in-time observation schema | done — `packages/common/schemas` |
| §79-80 Provider abstraction + failover | done — Yahoo Finance (prices), FRED (rates); unit-tested against mocked HTTP |
| §7.1-§9, §15-16 Feature engine (returns, rates, technical, DXY/cross-asset) | done, versioned (`FEATURE_SET_VERSION`) |
| §21, §59, §74-75 Rule-based regime classifier | done (v1, unvalidated thresholds — see below) |
| §26, §60, §73-78 Deterministic Gold Risk Score ("Model A") | done, weights unvalidated (see below) |
| §77 Confirmation/invalidation logic | done, recomputed if the ML ensemble moves the bias bucket |
| §15 Key levels (support/resistance) | done, simple swing high/low only |
| §27 Immutable prediction object + driver attribution | done |
| §9, §30, §36 Friday snapshot generator | done — `packages/snapshots/friday.py` |
| §33 Leakage protection | done — enforced in `data_access.py`, tested in `tests/data_quality/` |
| §82-83 Unit/integration/data-quality tests + CI | done (no historical-episode regression tests yet, see below) |

## Done: Agent Team + ML continuation (plan sections 12, 17-20, 23-25, 29, 31, 50, 61-62)

| Plan section | Status |
|---|---|
| §12 CFTC COT positioning | done — `CftcCotProvider` (Socrata API, unverified field names, see below), crowding/liquidation-risk features, wired into the deterministic score's positioning component |
| §17-20 News event pipeline | done — `NewsArticle`/`NewsEventRecord` tables, dedup (§17 step 1), source-tier confidence capping (§19), `NewsEvent` Pydantic schema enforcing a typed `transmission_chain` terminating in `gold_up`/`gold_down` |
| §21 Regime persistence + change detection | done — `RegimeAgent` now actually writes to the `regimes` table (nothing did before) and reports `changed`/`previous_regime` |
| §23 Prediction targets/labels | done — `packages/backtesting/labels.py`: 1d/5d return, direction, and ±1% significant-move labels |
| §24-25 Model B (ML) + Ensemble | done as real, tested *infrastructure* — `packages/models/` (LogisticRegression/RandomForest/LightGBM, a common fit/predict_proba interface, a `ModelVersion` registry) and `packages/models/ensemble.py`. **Inactive by construction**: no model has real training data to fit on in this environment, so nothing is ever promoted past `status="candidate"` here — see below |
| §29 Walk-forward validation | done — `packages/backtesting/walk_forward.py`, chronological rolling windows only, never a random split |
| §31 Calibration/classification metrics | done — AUC, PR-AUC, Brier, log-loss, Expected Calibration Error |
| §50 Agent Architecture (all 8 agents) | done — `packages/agents/`: MarketDataAgent, RatesMacroAgent, PositioningAgent, NewsEventAgent, RegimeAgent, PredictionAgent, ExplanationAgent, BacktestAgent, coordinated by `orchestrator.run_weekly_pipeline`. News Event Agent and Explanation Agent are genuinely Claude-backed (`anthropic.messages.parse` / `.create`); both take their client as an argument so tests never make a live call |
| §58 "LLM output must conform to Pydantic schema" | done — `NewsEvent` is validated via `client.messages.parse(..., output_format=NewsEvent)`, never free-text |
| Explanation Agent "must never modify the score" (§50) | done by construction — `explain()` returns a plain string; the orchestrator assigns it to `PredictionPayload.narrative` only, after every numeric field is already fixed, and `Prediction` rows are still never updated in place |
| `/model/health` (§43) | done |

## Explicitly not real yet (stubbed, not faked)

- **Probabilities** (`Prediction.probabilities`): always `{}`. Sections 1,
  26, 32 require calibration before external visibility, which requires an
  *active* ML model with walk-forward-validated calibration — see below.
- **Confidence**: a signal-agreement/data-completeness heuristic, not a
  calibrated probability of correctness.
- **Fed expectations** (phase 3 / §11): component pinned neutral. No free
  public source for Fed funds futures / meeting-probability data has been
  identified yet.
- **ETF flows, options** (§13-14): no free data source wired up.
- **Macro calendar / surprise engine / event risk score** (§38-39): not
  started; `Prediction.event_risks` is always `[]`.
- **No ML model is ever active in this environment.** `train_and_register`
  always writes `status="candidate"`; promotion to `"active"` (the only
  status `packages/models/ensemble.py` reads) is a deliberate, separate
  step a human takes after reviewing real walk-forward metrics (plan
  section 86). Since this sandbox has no outbound access to ingest real
  history, no model has ever actually been trained on real data here —
  the training/evaluation pipeline is tested against synthetic fixture
  data only (see `tests/integration/test_train.py`), which proves the
  mechanics work, not that any particular model is good.
- **Live news feed**: `NewsEventAgent.process_article` genuinely classifies
  a given article; nothing polls a real news source and calls it yet. `run()`
  reports `status="unavailable"` honestly instead of pretending to have
  polled anything.
- **Weekend re-scoring** (Saturday/Sunday updates, prediction deltas,
  §36-37, phase 11): the orchestrator produces the Friday baseline only;
  re-running it with updated weekend news/inputs and diffing against the
  baseline is the natural next step but isn't wired up.
- **Alerts** (§46, phase 13), **paper trading** (§67, phase 14), **trading
  strategy layer** (§68, phase 15): not started.
- **Dashboard secondary pages** (`/weekend`, `/drivers`, `/news`, `/rates`,
  `/positioning`, `/backtest`, `/models`, `/system`, §45): not started,
  only `/` (overview, now including the narrative and ML score) exists.
- **Historical regression tests** (§83 — COVID crash, 2022 rate shock,
  Ukraine invasion, Fed pivots, banking crisis): needs the historical
  backfill to actually run first (blocked on network access wherever this
  runs — see below), so the fixtures aren't real market data yet.

## Documented approximations to revisit

- **FRED `available_at`**: fixed at 21:30 UTC on the observation date as a
  stand-in for the real H.15 release calendar.
- **Yahoo Finance `available_at`**: set equal to `observed_at` (same-day
  availability assumed for daily OHLCV).
- **CFTC COT `available_at`**: fixed at 19:30 UTC (~15:30 ET) on the Friday
  following the report date, matching the CFTC's stated release schedule.
- **CFTC field names are not live-verified** (`packages/ingestion/providers/cftc_cot.py`):
  this sandbox has no network access to `publicreporting.cftc.gov`, so the
  Socrata column names (`m_money_positions_long_all`, etc.) come from
  public documentation, not a live response. Confirm against
  `https://publicreporting.cftc.gov/resource/72hh-3qpy.json?$limit=1`
  before trusting this in production.
- **Regime thresholds** and **score weights** (`packages/signals/deterministic.py: WEIGHTS`)
  are the plan's own starting assumptions (§73-75), not yet statistically
  validated (§25).
- **News Event Agent's transmission chain is single-path, not multi-path**:
  plan section 20 describes multiple *candidate* causal chains per event
  with the regime engine picking the dominant one; the agent here is given
  the current regime as context and asked for its single best-estimate
  chain directly, rather than enumerating alternatives for something else
  to pick from. Simpler, but a v1 simplification — see the docstring in
  `packages/agents/news_event_agent.py`.
- **Cross-asset component** only uses DXY and silver-vs-gold (the two
  unambiguous rows in §16's table); copper/VIX/SPX are read by the regime
  classifier but deliberately left out of the score.
- **Missing features are imputed as 0.0** in `packages/models/ensemble.py:
  build_feature_vector` — a documented simplification; a production
  trainer would carry a real imputer alongside the model artifact.

## Infra follow-ups

- TimescaleDB extension (§5, listed as optional) not enabled — plain
  Postgres is enough at this data volume.
- Celery/Temporal (§5) not needed yet — APScheduler runs the scheduled jobs.
- Redis is provisioned in `docker-compose.yml` but unused by application code.
- Model artifacts are saved to local disk (`infra/models/*.joblib`, gitignored)
  — move to real object storage (S3/GCS) before any production use.
- No live ingestion (market data, COT, or news) has run in this repo's own
  dev environment: its sandbox has no outbound access to
  `query1.finance.yahoo.com`, `api.stlouisfed.org`, `publicreporting.cftc.gov`,
  or a live news source. Providers are unit-tested against mocked HTTP
  responses instead of fabricated "real" data — run
  `python -m apps.worker.backfill` somewhere with that network access to
  actually populate history, then a real `ANTHROPIC_API_KEY` unlocks the
  News/Explanation agents.
