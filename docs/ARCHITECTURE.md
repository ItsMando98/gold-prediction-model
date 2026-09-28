# Architecture

## Layers

```
packages/ingestion    - vendor-agnostic provider ABCs + Yahoo Finance / FRED
                         implementations + failover pipeline + provider_health
packages/common       - Observation/Bar schemas, DB models, config, logging
packages/features     - point-in-time data access, indicators, versioned
                         feature registry
packages/regimes      - rule-based regime classifier
packages/signals       - deterministic Gold Risk Score ("Model A"), confidence,
                         key levels, confirmation/invalidation
packages/snapshots     - Friday snapshot generator that ties the above into an
                         immutable Prediction
apps/api               - FastAPI, read-only over the predictions/regime/health tables
apps/worker             - APScheduler jobs (daily ingestion, weekly prediction) + backfill CLI
apps/dashboard          - Next.js App Router, server-rendered overview page
```

Data flows one way: providers → raw store (`market_prices`, `rates`) →
features → regime + score → predictions. Nothing downstream writes back
upstream, and predictions are never updated in place (plan section 27).

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
contributes `weight * (score - 50)` to the final score. Components without
underlying data (Fed, positioning, news — later phases) stay pinned at
neutral with `available=False` rather than being faked; `data_completeness`
and `confidence` both discount for this explicitly.

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

## Adding a provider

Implement `PriceProvider` or `RateProvider` from `packages/ingestion/base.py`,
add the vendor ticker mapping to `configs/providers/symbols.yaml`, and put
it first (or as a fallback) in the provider list passed to
`ingest_price_history`/`ingest_rate_history` in `apps/worker/jobs.py`. Every
attempt — success or failure — is recorded in `provider_health`
automatically by the pipeline.
