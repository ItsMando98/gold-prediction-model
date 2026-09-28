# Gold Prediction Model

A continuously running Gold Market Intelligence & Prediction System: it collects
market/macro/positioning/news data, builds point-in-time-correct features,
classifies the current market regime, and produces an explainable, immutable
prediction for gold (XAUUSD) — starting with the "Friday close → Monday"
baseline. An AI Agent Team (plan section 50) coordinates the pipeline, and an
ML baseline (LightGBM/RandomForest/LogisticRegression) is ready to blend into
the deterministic score once a model is trained and promoted.

This repository implements **Phase 0 (Foundation)**, the **First AI Coding
Agent Sprint (Tasks 1-12)**, and a follow-on continuation covering **CFTC
positioning (phase 4), news intelligence (phase 5), the full 8-agent Agent
Team (section 50), and the walk-forward ML pipeline (phases 8-9, section
25's ensemble)** from `docs/Gold_Prediction_Model_AI_Coding_Agent_Plan.md`.
Fed expectations, ETF flows/options, the macro calendar, and probability
calibration are still open — see `docs/ROADMAP.md` for exactly what's built
vs. what's next.

## Architecture

```
providers (Yahoo Finance, FRED, CFTC COT) -> ingestion pipeline
    -> Postgres (market_prices, rates, cot_positions, news_articles/news_events)
    -> feature engine (point-in-time correct)
    -> Agent Team (packages/agents/, plan section 50):
         PositioningAgent -> RatesMacroAgent -> NewsEventAgent (Claude)
         -> PredictionAgent (deterministic + optional active ML model)
         -> RegimeAgent -> ExplanationAgent (Claude)
    -> one immutable Prediction row -> FastAPI -> Next.js dashboard
```

See `docs/ARCHITECTURE.md` for details on each layer, the point-in-time
correctness contract every module depends on, and how the Agent Team and ML
ensemble fit together without ever updating a Prediction row in place.

## Quickstart (Docker)

```bash
cp .env.example .env
# set FRED_API_KEY (https://fred.stlouisfed.org/docs/api/api_key.html)
# set ANTHROPIC_API_KEY (https://console.anthropic.com/settings/keys) to enable
# the News Event Agent and Explanation Agent -- optional, everything else works without it
docker compose up --build
```

- API: http://localhost:8000 (docs at `/docs`, health at `/health`)
- Dashboard: http://localhost:3000
- Postgres: localhost:5432

The `api` container runs `alembic upgrade head` on boot. The `worker`
container schedules daily ingestion (weekdays 22:00 UTC: prices, rates, COT)
and the weekly Agent Team run (Fridays 21:15 UTC) via APScheduler.

**Network requirement:** ingestion needs outbound HTTPS to
`query1.finance.yahoo.com` (market data), `api.stlouisfed.org` (rates,
requires `FRED_API_KEY`), and `publicreporting.cftc.gov` (COT positioning,
no key required). The News/Explanation agents need `api.anthropic.com`. If
your environment blocks these (as this project's own dev sandbox does), all
of this is still fully unit-tested against mocked HTTP/fake clients — see
`tests/integration/test_yahoo_provider.py`, `test_fred_provider.py`,
`test_cftc_cot_provider.py`, and `tests/anthropic_fakes.py` — but you'll
need to run ingestion somewhere with that access to get real data.

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

### Run the full Agent Team pipeline manually

```python
import asyncio
from packages.common.db.session import get_sessionmaker
from packages.agents.orchestrator import run_weekly_pipeline

session = get_sessionmaker()()
report = asyncio.run(run_weekly_pipeline(session))  # narrative is best-effort without ANTHROPIC_API_KEY
print(report.prediction.regime, report.prediction.risk_score, report.prediction.bias)
for r in report.agent_results:
    print(r.agent, r.status, r.detail)
```

Or, for just the deterministic core without agent orchestration:

```python
from packages.snapshots.friday import generate_prediction

prediction = generate_prediction(session)
```

Either is the object the plan's first milestone (section 88) is judged
against: *"Based only on information that was actually available at
Friday's close, how bearish or bullish was gold for the next Monday
session, and why?"*

### Train and (carefully) activate an ML model

```python
from packages.backtesting.dataset import build_dataset
from packages.models.train import train_and_register

dates = [...]  # e.g. every Friday close over your backfilled history
df = build_dataset(session, "XAUUSD", dates)
version = train_and_register(session, df, "lightgbm", name="baseline")
print(version.metrics)  # walk-forward AUC/Brier/log-loss -- review before promoting

# Only after you've reviewed the walk-forward metrics yourself:
version.status = "active"
session.commit()
```

No model is ever auto-promoted to `"active"` — `packages/models/ensemble.py`
only reads that status, and promotion is a deliberate human decision (plan
section 86: "backtest before live trust").

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
The Claude-backed agents (News Event, Explanation) are tested against fake
clients in `tests/anthropic_fakes.py` — no test ever makes a live API call
or requires an API key.

CI (`.github/workflows/ci.yml`) runs the same suite against a Postgres
service container on every push/PR.

## API

| Endpoint | Description |
|---|---|
| `GET /health` | liveness check |
| `GET /prediction/current?symbol=XAUUSD` | latest prediction (includes `narrative` and `ml_score`) |
| `GET /prediction/history?symbol=XAUUSD&limit=50` | prediction history |
| `GET /prediction/{id}` | a specific immutable prediction |
| `GET /regime/current?symbol=XAUUSD` | current regime, persisted by the Regime Agent |
| `GET /data/health?hours=48` | provider health ledger |
| `GET /model/health` | registered ML model versions and which one (if any) is active |

## What's deliberately not real yet

- **`probabilities` is always `{}`.** Plan sections 1, 26 and 32 are explicit
  that probabilities must not be derived directly from a score and must be
  calibrated against walk-forward backtest results before being shown.
- **`confidence` is a heuristic**, not a calibrated probability of
  correctness — see the docstring in `packages/signals/confidence.py`.
- **No ML model is ever active in this environment.** The training/ensemble
  pipeline is real and tested (against synthetic fixture data, since this
  sandbox can't ingest real history), but `train_and_register` never
  auto-promotes anything past `status="candidate"`.
- **Fed expectations** stay a neutral stub — no free data source identified
  yet. ETF flows, options, and the macro calendar aren't started.
- **No live news feed is connected.** The News Event Agent genuinely
  classifies a given article into a structured event; nothing polls a real
  source for articles yet.
- Every `Prediction.model_versions` carries `"calibrated": false` so no
  API/dashboard consumer can mistake any of this for a validated signal.

See `docs/ROADMAP.md` for the full phase-by-phase status against the plan.
