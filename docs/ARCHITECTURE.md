# Architecture

## Layers

```
packages/ingestion    - vendor-agnostic provider ABCs + Yahoo Finance / FRED /
                         CFTC COT implementations + failover pipeline + provider_health
packages/common       - Observation/Bar/CotRecord/NewsEvent schemas, DB models,
                         config, logging
packages/news         - source-tier credibility mapping, article dedup
packages/features     - point-in-time data access, indicators, versioned
                         feature registry (prices, rates, COT, news aggregation)
packages/regimes      - rule-based regime classifier
packages/signals       - deterministic Gold Risk Score ("Model A"), confidence,
                         key levels, confirmation/invalidation
packages/snapshots     - Friday payload builder + single-insert persistence
packages/backtesting   - point-in-time dataset builder, forward-return labels,
                         walk-forward splits, classification/calibration metrics
packages/models         - ML baselines (Model B), ModelVersion registry,
                         training pipeline, deterministic+ML ensemble
packages/agents         - the 8 specialist agents (plan section 50) + orchestrator
apps/api               - FastAPI, read-only over predictions/regime/health/model tables
apps/worker             - APScheduler jobs (daily ingestion, weekly Agent Team run) + backfill CLI
apps/dashboard          - Next.js App Router, server-rendered overview page
```

Data flows one way: providers → raw store (`market_prices`, `rates`,
`cot_positions`, `news_articles`/`news_events`) → features → regime + score
→ predictions. Nothing downstream writes back upstream, and predictions
are never updated in place (plan section 27) — see "Agent Team" below for
how the orchestrator still fits a narrative and an ML score into that rule
rather than around it.

## Point-in-time correctness

This is the one invariant every other design decision serves.

- `packages/common/schemas/observation.py` defines `PointInTimeRecord`
  (`observed_at`, `available_at`, `ingested_at`, `revision`) and enforces
  `observed_at <= available_at <= ingested_at` at construction time via a
  Pydantic validator. `Bar` and `Observation` both inherit it.
- `packages/features/data_access.py` is the *only* place allowed to read
  `market_prices`/`rates` for feature computation. Every query filters on
  `available_at <= as_of`, never on `observed_at`. For series that get
  revised, it resolves each `observed_at` to the most recent revision whose
  `available_at` had already passed by `as_of`.
- `tests/data_quality/test_leakage.py` asserts this directly: a
  later-arriving/revised observation with `available_at > as_of` must not
  appear in a query for that `as_of`.
- A revision is tied to its own `available_at`/`ingested_at` — two rows
  can't share `(source, symbol, observed_at, revision)` with different
  `available_at` values (that's what the unique constraint means, and
  Postgres will reject a batch that tries to upsert two of them in the
  same statement). A restated value gets the *next* revision number, not
  a mutated `available_at` on the same revision.
- News events are gated the same way, just on a different column: an
  event can never be knowable before the article it came from was
  published, so `recent_news_events` filters on `NewsArticle.published_at`,
  not on when the News Event Agent happened to run its extraction.
- The **one** deliberate exception is `full_price_history` in
  `data_access.py`, used only by `packages/backtesting/labels.py` to
  compute forward-return labels — looking forward from `as_of` is the
  entire point of a label. Using it inside a feature definition is the
  leakage bug this whole design exists to prevent.

If you add a new data source or feature, read through `data_access.py` and
respect this or you will introduce leakage that silently overstates
backtest performance later.

## Feature engine

`packages/features/registry.py` holds a version string (`FEATURE_SET_VERSION`)
and a list of registered compute functions. Each function in
`packages/features/definitions/` takes a `FeatureContext` (pre-fetched,
point-in-time price/rate series for all core symbols) and returns a flat
`dict[str, float | None]`. `packages/features/engine.py` builds the context,
runs every registered function, and upserts the merged dict into
`FeatureSnapshot` keyed on `(symbol, as_of, feature_set_version)` — so the
same snapshot is never duplicated on re-run, and bumping the version
creates a new, independently reproducible snapshot rather than silently
changing history.

## Deterministic score ("Model A")

`packages/signals/deterministic.py` computes eight weighted components
(rates, USD, Fed, positioning, technical, news, oil/inflation, cross-asset;
weights from plan section 73). Each component is 0-100 (50 = neutral) and
contributes `weight * (score - 50)` to the final score. Positioning
(crowding/liquidation-risk from CFTC COT) and news (aggregated,
tier-capped News Event Agent output) are real whenever data exists for a
given `as_of`; Fed stays pinned at neutral (`available=False`) because no
free data source has been identified for it yet. `data_completeness` and
`confidence` both discount for whatever's actually missing.

The oil/inflation component deliberately flips sign based on whether real
yields are also rising (plan section 10: oil's effect on gold is
regime-dependent, never a fixed sign) — see
`test_oil_component_flips_sign_with_regime` for the exact scenario.

## Regime classifier

`packages/regimes/classifier.py` is a straight port of the plan's own
section 21/74/75 threshold rules — intentionally the "first, simple"
baseline the plan asks for (section 59) before any HMM/GMM/ML classifier.
It only ever emits regimes derivable from price/rate data; regimes that
require COT/ETF/news (`POSITIONING_LIQUIDATION`, `POSITIONING_SHORT_SQUEEZE`,
`GOLD_SPECIFIC_FLOW`, `INFLATION_HEDGE`) are structurally unreachable until
those phases exist, and fall back to `MIXED` instead of guessing.

## ML models and the ensemble (plan sections 24-25, 61-62)

`packages/backtesting/dataset.py` builds a point-in-time dataset: one row
per `as_of`, with the exact feature vector `compute_features` would have
produced live, paired with forward-return labels from
`packages/backtesting/labels.py`. `packages/models/train.py` walk-forward
evaluates a model type (`packages/backtesting/walk_forward.py` — rolling
chronological windows, never a random split) and, if asked to register,
fits a final model on the full dataset, saves the artifact
(`packages/models/io.py`), and writes a `ModelVersion` row with
`status="candidate"`.

Nothing here ever sets `status="active"` itself. `packages/models/ensemble.py:
get_active_model_version` only ever reads an `active` row, so a model
stays inert — the deterministic score runs alone — until a human promotes
one after reviewing real walk-forward metrics (plan section 86: "backtest
before live trust"). When a model is active, `PredictionAgent` blends its
probability into the deterministic score (`ensemble.combine`) and, if that
blend crosses a bias-bucket boundary (plan section 26), recomputes
bias/confirmation/invalidation/contradictions against the *blended* score
before anything is persisted — see the docstring on
`packages/agents/prediction_agent.py`.

## Agent Team (plan section 50)

`packages/agents/` implements the plan's 8 specialist agents as
independently testable modules, each returning a uniform `AgentResult`:

| Agent | What it actually does |
|---|---|
| MarketDataAgent | thin wrapper over the ingestion pipeline (collect/validate/store) |
| RatesMacroAgent | summarizes rate levels/changes/curve slope; reports Fed data honestly as unavailable |
| PositioningAgent | CFTC COT ingestion + crowding/liquidation-risk summary |
| NewsEventAgent | **Claude-backed** — `classify_article` calls `client.messages.parse(..., output_format=NewsEvent)` so the model's read of an article is a schema-validated, causally-explicit `transmission_chain`, never free-text sentiment (plan section 58) |
| RegimeAgent | runs the classifier, persists a `RegimeSnapshot`, detects a change vs. the last one for that symbol |
| PredictionAgent | assembles features, computes the deterministic score, blends in an active ML model if one exists |
| ExplanationAgent | **Claude-backed** — turns a *finalized* `PredictionPayload` into prose; it has no mechanism to write to any numeric field, so it structurally cannot "explain" a prediction into a different score |
| BacktestAgent | wraps dataset-building + walk-forward evaluation/training for reporting |

`packages/agents/orchestrator.py: run_weekly_pipeline` runs
Positioning → RatesMacro → (News, if articles are supplied) →
Prediction → Regime → Explanation, then makes the single INSERT
(`persist_prediction_payload`) that turns all of it into one immutable
`Prediction` row. This is why `packages/snapshots/friday.py` is split into
`build_prediction_payload` (pure computation) and `persist_prediction_payload`
(the one write): the Explanation Agent's narrative and an active model's
score have to exist *before* that insert, because nothing about a
`Prediction` is ever updated afterward.

Both Claude-backed agents take their `anthropic.Anthropic` client as an
argument (constructed via `get_client()`, which raises a clear
`ProviderError` if `ANTHROPIC_API_KEY` isn't configured, exactly like the
FRED/CFTC providers do for their own missing keys). Tests inject a fake
client (`tests/anthropic_fakes.py`) and never make a live call. In
`orchestrator.py`, a failure to generate a narrative is caught narrowly
(`ProviderError` only — a missing key or a real API error) and downgraded
to a best-effort skip so it never blocks the numeric prediction from being
persisted; any other exception is a bug and is allowed to propagate rather
than being silently swallowed (plan section 51).

## Adding a provider

Implement `PriceProvider`, `RateProvider`, or `PositioningProvider` from
`packages/ingestion/base.py`, add the vendor ticker mapping to
`configs/providers/symbols.yaml`, and put it first (or as a fallback) in
the provider list passed to `ingest_price_history`/`ingest_rate_history`/
`ingest_positioning_history` — wired up in `apps/worker/jobs.py` (daily)
and `packages/agents/market_data_agent.py`/`positioning_agent.py` (via the
orchestrator). Every attempt — success or failure — is recorded in
`provider_health` automatically by the pipeline.

## Worker scheduling

`apps/worker/main.py` schedules two jobs: `ingest_daily` (weekdays, prices
+ rates + COT) and `generate_weekly_prediction` (Fridays, the full Agent
Team pipeline via `orchestrator.run_weekly_pipeline`). The weekly job
doesn't re-ingest market data itself (`ingest_market_data=False`) since the
daily job already keeps things current; it always attempts a narrative
(`generate_narrative=True`) and simply gets `narrative=None` back if
`ANTHROPIC_API_KEY` isn't configured. No live news feed is connected, so
`news_articles` is never populated automatically yet — see
`docs/ROADMAP.md`.

## Dashboard (plan section 44)

`apps/dashboard/app/page.tsx` is a server component that fetches the
current prediction and recent history, then composes them from
`apps/dashboard/components/`: `RiskGauge` (a diverging linear gauge —
bullish/neutral/bearish is a polarity, not a magnitude, so it gets the
blue/gray/red diverging pair, not a single accent color), `StatTile`,
`DriverBars` (a diverging horizontal bar chart with a table-view toggle
for accessibility), `RiskHistoryChart` (a line-vs-baseline chart with a
custom hover crosshair, area fill split at the neutral=50 line rather than
at zero), and `StatusList` (confirmation/invalidation as icon+label, never
color alone). All of it follows the design-system method in the bundled
`dataviz` skill — `apps/dashboard/app/globals.css` defines the token set
(diverging pair, sequential ramp, fixed status colors, chrome/ink) as CSS
custom properties, redefined under both a `prefers-color-scheme: dark`
media query and a `data-theme="dark"` override so `ThemeToggle` (which
also fixes what it displays to the theme actually resolved — explicit
choice, else live OS preference — rather than only the last click) can win
over the OS setting. Colors are never chosen per-chart; every component
reads the same custom properties.
