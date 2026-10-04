# upay Pulse - Agent Liquidity & Risk Intelligence (Track 05 backend)

FastAPI backend (modular) + LightGBM quantile forecasting + Isolation Forest anomaly detection +
LangChain / Google Gemini daily brief. **All data is synthetic.**

## 1. Setup (Python virtual environment + PostgreSQL)

Full stack in Docker (API + UI + Postgres) from the **repository root** (parent of this folder):

```bash
cp backend/.env.example backend/.env   # if you have not already
docker compose up --build              # first run seeds data; UI at http://localhost:3000
```

Host-based API (this folder) + Postgres only:

```bash
docker compose up -d db              # PostgreSQL 16 on localhost:5434 (user/pass/db = upay / upay / upay_pulse)
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # DATABASE_URL is preset; add GOOGLE_API_KEY (optional - template fallback works without it)
```
No Docker? Install PostgreSQL yourself, create a database, and set `DATABASE_URL=postgresql://USER:PASS@HOST:5432/DB`.

## 2. Migrate -> load data -> (train) -> serve

```bash
python3 -m scripts.generate_data     # applies pending migrations, then bulk-loads 300 agents (~2M hourly rows) with COPY (~1-2 min)
uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs   (ships with trained models in artifacts/)
python3 -m scripts.smoke_test        # hits every endpoint, checks DB persistence
python3 -m scripts.train             # OPTIONAL retrain: reads from PostgreSQL, writes artifacts/ + a model_runs row
```
The generator is seeded, so it reproduces exactly the data the shipped models were trained on (keep N_AGENTS=300 and the default dates).
Slow machine? `TRAIN_SAMPLE_FRAC=0.3 N_ESTIMATORS=250`.

## 2b. Database: raw asyncpg + versioned SQL migrations

No ORM. The API is fully async (`asyncpg` pool, `async def` endpoints, LangChain `ainvoke`); CPU-heavy model inference runs in a worker thread.

```bash
python3 -m scripts.migrate status              # list applied / pending migrations
python3 -m scripts.migrate up [--to 2]         # apply pending (each in its own transaction, advisory-locked)
python3 -m scripts.migrate down [--steps 1]    # roll back the newest N   (or --to VERSION)
python3 -m scripts.migrate new add_something   # scaffold app/db/migrations/0003_add_something.sql
python3 -m scripts.migrate reset --yes         # dev only: down to 0, then up
```
Migration files are `app/db/migrations/NNNN_name.sql` with `-- migrate:up` and `-- migrate:down` sections.
Applied versions are tracked in `schema_migrations` with a SHA-256 checksum: **editing an already-applied migration is refused**
(create a new one instead). The API refuses to start if migrations are pending (set `AUTO_MIGRATE=true` in `.env` to auto-apply in dev).

| Table | Purpose |
|---|---|
| `agents`, `hourly`, `daily`, `weather`, `anomaly_labels` | Synthetic data (migration 0001). `hourly` has PK (agent_id, timestamp) + timestamp index; the API queries it by time window |
| `alert_reviews` | Current analyst decision per alert (confirmed / dismissed) - migration 0002 |
| `feedback_log` | Append-only history of every decision = future training labels (feedback loop) |
| `audit_log` | Who did what (JSONB detail). Review + feedback + audit are written in ONE transaction |
| `model_runs` | Metrics + calibration of every training run (served by `GET /metrics`) |
| `schema_migrations` | Migration bookkeeping |

## 3. Project layout

```
app/
  core/       config (pydantic-settings), constants, utils
  db/         pool (asyncpg), migrate (runner), migrations/*.sql, queries (COPY bulk load + raw SQL helpers)
  data/       calendar_bd (Eid/Ramadan/salary...), generator (synthetic ecosystem), loader (reads PostgreSQL)
  ml/         features, forecasting (LightGBM quantiles + baseline), liquidity (business rules),
              explain (native SHAP), anomaly (Isolation Forest), rebalance (greedy route),
              simulation (cash+float simulator), pipeline (train + evaluate)
  services/   store, liquidity_service, anomaly_service, llm_service (LangChain+Gemini), brief_service
  api/        deps, routes
scripts/      migrate, generate_data, train, smoke_test
artifacts/    models, calibration.json, metrics.json, alert review log   (created by train)
data_store/   DATA_ASSUMPTIONS.md                                           (created by generate_data)
```

## 4. Key endpoints  (`as_of` defaults to DEMO_AS_OF = 2026-05-20 08:00, eight days before Eid-ul-Adha)

| Endpoint | What it does |
|---|---|
| `GET /risk?level=HIGH` | Stockout-risk table for all agents (probability, expected time, top-up needed) |
| `GET /agents/{AG0007}/forecast` | 24h P10/P50/P90 flows, projected cash & e-float, risk, advice (EN/BN), SHAP drivers, 7-day-MA comparison |
| `GET /rebalance?district=Dhaka` | Greedy DSO cash-delivery route (float shortfalls = digital transfers) |
| `GET /alerts` / `POST /alerts/{id}/review` | Anomaly queue + human approve/dismiss (logged as future labels) |
| `GET /alerts/{id}/narrative` | LLM investigation narrative grounded in structured evidence |
| `GET /brief` | LangChain + Gemini manager brief (template fallback if no key) |
| `GET /metrics` | Evaluation: vs baseline, calibration, policy simulation, fairness, anomaly |

## 5. How it works

* **Two balances per agent** (cash and e-float). Net flow = cash-out - cash-in: positive drains cash, negative drains float.
* **One model, both risks**: LightGBM quantile regression (P10/P50/P90) of hourly net flow, normalised per agent.
* **Cumulative P90 band**: per-hour quantiles are combined as `cumP50 + k * z90 * sqrt(sum sigma^2)`; `k` is calibrated on a
  validation window so the daily PEAK-drain P90 covers ~90% of outcomes. The baseline (7-day same-hour moving average) is
  calibrated the same way, so the comparison is fair.
* **Business rules are separate from ML** (`ml/liquidity.py`): top-up = P90 need + reserve - balance; risk level from stockout probability.
* **Leakage-safe features**: only data >= 24h old (same-hour lags, 14-day means shifted 2 days) + calendar/weather/profile.
* **LLM guard**: Gemini only writes up structured facts; JSON is treated as untrusted data; recommendations only.

## 6. Honest caveats (say them in the pitch)

* Synthetic data: the model learns the patterns we injected. Defences: hidden daily agent shocks, a time-based holdout that contains an unseen Eid, baselines, calibration.
* Recorded demand = attempted demand (stockouts do not censor targets). Real data would need demand-censoring handling.
* Weather is treated as a perfect forecast. Eid/Ramadan dates are approximate.
* Fairness check is by area type and division only; stockout-probability is an approximation (max over hours of a normal tail).
