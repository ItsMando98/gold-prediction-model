# Roadmap: plan sections vs. what's implemented

Full plan: `docs/Gold_Prediction_Model_AI_Coding_Agent_Plan.md`. This tracks
status against it so nobody has to diff the whole document to find out
what's real.

## Done (Phase 0 + First Sprint, plan sections 53-54 & 87, Tasks 1-12)

| Plan section | Status |
|---|---|
| §6 Repository structure | done (`apps/`, `packages/`, `configs/`, `research/`, `tests/`, `infra/`, `docs/`) |
| §49 Point-in-time observation schema | done — `packages/common/schemas` |
| Postgres migrations | done — Alembic, `market_prices`, `rates`, `features`, `regimes`, `predictions`, `prediction_drivers`, `provider_health` |
| §79-80 Provider abstraction + failover | done — Yahoo Finance (prices) + FRED (rates), health-ledger, unit-tested against mocked HTTP |
| §7.1-§9, §15-16 Feature engine (returns, rates, technical, DXY/cross-asset) | done, versioned (`FEATURE_SET_VERSION`) |
| §21, §59, §74-75 Rule-based regime classifier | done (v1, unvalidated thresholds — see below) |
| §26, §60, §73-78 Deterministic Gold Risk Score ("Model A") | done, weights unvalidated (see below) |
| §77 Confirmation/invalidation logic | done |
| §15 Key levels (support/resistance) | done, simple swing high/low only |
| §27 Immutable prediction object + driver attribution | done |
| §9, §30, §36 Friday snapshot generator | done — `packages/snapshots/friday.py` |
| §43 API (subset) | done — `/health`, `/prediction/*`, `/regime/current`, `/data/health` |
| §44 Dashboard (overview only) | done — Next.js `/` page |
| §33 Leakage protection | done — enforced in `data_access.py`, tested in `tests/data_quality/` |
| §82-83 Unit/integration/data-quality tests + CI | done (no historical-episode regression tests yet, see below) |

## Explicitly not real yet (stubbed, not faked)

- **Probabilities** (`Prediction.probabilities`): always `{}`. Sections 1,
  26, 32 require calibration before external visibility; that requires the
  walk-forward backtest (phase 9/11), which doesn't exist yet.
- **Confidence**: a signal-agreement/data-completeness heuristic, not a
  calibrated probability of correctness.
- **Fed expectations** (phase 3 / §11): component pinned neutral.
- **Positioning — CFTC COT, ETF flows** (phase 4 / §12-13): component
  pinned neutral. No `cot_positions`/`etf_flows` tables yet.
- **News/event intelligence** (phase 5 / §17-20): component pinned neutral.
  No `news_articles`/`news_events` tables yet.
- **Options module** (§14): not started.
- **Macro calendar / surprise engine / event risk score** (§38-39): not
  started; `Prediction.event_risks` is always `[]`.
- **ML models** (Model B/C/D, §28-30 phase 9), **ensemble** (§25, phase
  10), **probability calibration** (§32, phase 9): not started.
- **Weekend re-scoring** (Saturday/Sunday updates, prediction deltas,
  §36-37, phase 11): `generate_prediction` produces the Friday baseline
  only; re-running it with updated weekend inputs and diffing against the
  baseline is the natural next step but isn't wired up.
- **Alerts** (§46, phase 13), **paper trading** (§67, phase 14), **trading
  strategy layer** (§68, phase 15): not started.
- **Dashboard secondary pages** (`/weekend`, `/drivers`, `/news`, `/rates`,
  `/positioning`, `/backtest`, `/models`, `/system`, §45): not started,
  only `/` (overview) exists.
- **Historical regression tests** (§83 — COVID crash, 2022 rate shock,
  Ukraine invasion, Fed pivots, banking crisis): needs the historical
  backfill to actually run first (blocked on network access wherever this
  runs — see below), so the fixtures aren't real market data yet.

## Documented approximations to revisit

- **FRED `available_at`** (`packages/ingestion/providers/fred.py`): fixed
  at 21:30 UTC on the observation date as a stand-in for the real H.15
  release calendar. Fine for MVP; replace with actual release timestamps
  before trusting close backtests around that boundary.
- **Yahoo Finance `available_at`**: set equal to `observed_at` (same-day
  availability assumed for daily OHLCV). Reasonable for daily bars; would
  need tightening for intraday horizons (plan's secondary scope).
- **Regime thresholds** (`REAL_YIELD_MOVE_BPS`, `US10Y_MOVE_BPS`,
  `DXY_MOVE_PCT`, `VIX_ELEVATED`, `VIX_STRESS`) and **score weights**
  (`packages/signals/deterministic.py: WEIGHTS`) are the plan's own
  starting assumptions (§73-75), explicitly not yet statistically
  validated (§25: "weights must be learned/validated rather than
  permanently hard-coded"). Phase 9's walk-forward backtest is the
  intended validation step.
- **Cross-asset component** only uses DXY and silver-vs-gold (the two
  unambiguous rows in §16's table). Copper, VIX, and SPX are read by the
  regime classifier but deliberately left out of the deterministic score
  because the plan itself calls their gold-direction effect conditional/
  context-dependent, and forcing a sign would be guessing.

## Infra follow-ups

- TimescaleDB extension (§5, listed as optional) not enabled — plain
  Postgres is enough at this data volume.
- Celery/Temporal (§5) not needed yet — APScheduler (explicitly named as
  the MVP choice) runs the two scheduled jobs.
- Redis is provisioned in `docker-compose.yml` but unused by application
  code yet (reserved for a future Celery migration / caching layer).
- No live ingestion has run yet in this repo's own dev environment: its
  sandbox has no outbound access to `query1.finance.yahoo.com` or
  `api.stlouisfed.org`. Providers are unit-tested against mocked HTTP
  responses instead of fabricated "real" data — run
  `python -m apps.worker.backfill` somewhere with that network access to
  actually populate history.
