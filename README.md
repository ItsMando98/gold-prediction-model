# Gold Prediction Model

A continuously running Gold Market Intelligence & Prediction System: it collects
market/macro data, builds point-in-time-correct features, classifies the current
market regime, and produces an explainable, immutable prediction for gold
(XAUUSD) — starting with the "Friday close → Monday" baseline.

This repository implements **Phase 0 (Foundation)** and the **First AI Coding
Agent Sprint (Tasks 1-12)** of `docs/Gold_Prediction_Model_AI_Coding_Agent_Plan.md`:
a deterministic, rule-based baseline (rates + USD + technical + a regime-aware
oil/inflation signal + limited cross-asset confirmation), end to end from raw
market data to an API and dashboard. Fed expectations, COT/ETF positioning,
news/event intelligence, ML models, and probability calibration are later
phases — see `docs/ROADMAP.md` for exactly what's built vs. what's next.

## Architecture

```
providers (Yahoo Finance, FRED) -> ingestion pipeline -> Postgres (market_prices, rates)
    -> feature engine (point-in-time correct) -> regime classifier
    -> deterministic Gold Risk Score -> immutable predictions table
    -> FastAPI -> Next.js dashboard
```

See `docs/ARCHITECTURE.md` for details on each layer and the point-in-time
correctness contract every module depends on.

## Quickstart (Docker)

```bash
cp .env.example .env
# set FRED_API_KEY in .env (https://fred.stlouisfed.org/docs/api/api_key.html)
docker compose up --build
```

- API: http://localhost:8000 (docs at `/docs`, health at `/health`)
- Dashboard: http://localhost:3000
- Postgres: localhost:5432

The `api` container runs `alembic upgrade head` on boot. The `worker`
container schedules daily ingestion (weekdays 22:00 UTC) and the weekly
Friday prediction (Fridays 21:15 UTC) via APScheduler.

**Network requirement:** ingestion needs outbound HTTPS to
`query1.finance.yahoo.com` (market data) and `api.stlouisfed.org` (rates,
requires `FRED_API_KEY`). If your environment blocks these (as this
project's own dev sandbox does), the provider/pipeline code is still fully
unit-tested against mocked HTTP responses — see `tests/integration/test_yahoo_provider.py`
and `tests/integration/test_fred_provider.py` — but you'll need to run
ingestion somewhere with that access.

## Local development (no Docker)

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

# Postgres must be running and reachable at DATABASE_URL (see .env.example)
alembic upgrade head

uvicorn apps.api.main:app --reload          # API on :8000
python -m apps.worker.main                  # scheduler

cd apps/dashboard && npm install && npm run dev   # dashboard on :3000
```

### Backfill historical data

```bash
python -m apps.worker.backfill --start 2015-01-01
```

### Generate a prediction manually

```python
from packages.common.db.session import get_sessionmaker
from packages.snapshots.friday import generate_prediction

session = get_sessionmaker()()
prediction = generate_prediction(session)
print(prediction.regime, prediction.risk_score, prediction.bias)
```

This is the object the plan's first milestone (section 88) is judged
against: *"Based only on information that was actually available at
Friday's close, how bearish or bullish was gold for the next Monday
session, and why?"*

## Tests

```bash
createdb gold_prediction_test   # once, via your local Postgres
pytest -q
ruff check .
```

Tests use a real Postgres database (`TEST_DATABASE_URL`, defaults to
`postgresql+psycopg://gold:gold@localhost:5432/gold_prediction_test`)
because the ingestion store relies on Postgres-specific `ON CONFLICT`
upserts and JSON columns — there's no SQLite fallback. `tests/data_quality/`
specifically covers leakage protection (plan section 33): that
`available_at`, not `observed_at`, gates what a point-in-time query can see.

CI (`.github/workflows/ci.yml`) runs the same suite against a Postgres
service container on every push/PR.

## API

| Endpoint | Description |
|---|---|
| `GET /health` | liveness check |
| `GET /prediction/current?symbol=XAUUSD` | latest prediction |
| `GET /prediction/history?symbol=XAUUSD&limit=50` | prediction history |
| `GET /prediction/{id}` | a specific immutable prediction |
| `GET /regime/current?symbol=XAUUSD` | current regime (derived from the latest prediction) |
| `GET /data/health?hours=48` | provider health ledger |

## What's deliberately not real yet

- **`probabilities` is always `{}`.** Plan sections 1, 26 and 32 are explicit
  that probabilities must not be derived directly from a score and must be
  calibrated (Platt/isotonic/Beta) against walk-forward backtest results
  before being shown. That calibration step (plan phases 9 & 11) doesn't
  exist yet, so the field is left empty rather than faked.
- **`confidence` is a heuristic**, not a calibrated probability of
  correctness — see the docstring in `packages/signals/confidence.py`.
- **Fed, positioning (COT/ETF), and news components are neutral stubs**
  (score 50, `available=False`) in the deterministic score — plan phases
  3-5 haven't been ingested yet.
- Every `Prediction.model_versions` carries `"calibrated": false` so no
  API/dashboard consumer can mistake this for a validated signal.

See `docs/ROADMAP.md` for the full phase-by-phase status against the plan.
