<!--
NOTE TO THE AUTHOR (this comment does not render on GitHub; delete it before publishing):
 - The Docker section follows your docker-compose.yml exactly. I could not see your Dockerfiles or
   scripts/docker_seed.sh, so the description of what the seed job does is inferred from the backend's scripts.
   Please check it against the real script.
 - In your compose file the backend does NOT wait for the seed job (no depends_on on `seed`), and the API loads the
   trained models at start-up. The steps below therefore run the seed to completion first.
-->

# upay Pulse: Agent Liquidity Intelligence

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![LightGBM](https://img.shields.io/badge/LightGBM-quantile%20models-2E8B57)
![scikit-learn](https://img.shields.io/badge/scikit--learn-Isolation%20Forest-F7931E?logo=scikitlearn&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-4-06B6D4?logo=tailwindcss&logoColor=white)
![MapLibre](https://img.shields.io/badge/MapLibre%20GL-H3%20hexagons-396CB2)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

**upay Pulse** is an AI-powered liquidity intelligence platform for mobile-money agent networks. It forecasts which agents will run out of cash or e-float in the next 24 hours, tells a district officer how much to deliver and in what order, and flags suspicious, declining or departing agents, with every recommendation explained in English and Bangla. It was built for the DIU CPC × upay AI Hackathon 2026 (Track 05) and runs on a reproducible synthetic dataset of 300 agents.

## Overview

A mobile-money agent is a small shop that holds two balances: physical cash and digital e-float. When either reaches zero during an open hour, the customer is turned away and both the agent and the operator lose volume. Today that is discovered after the fact.

upay Pulse moves the decision a day earlier. A pooled **LightGBM quantile model** forecasts hourly net cash flow as a low, middle and bad-day case, a calibration layer turns those hourly quantiles into a stockout probability and a top-up amount, and a route planner decides which agents one cash van should visit. The same data feeds an **Isolation Forest** anomaly monitor, a churn early-warning model, a peer-relative performance score, and a **census-weighted coverage map** that ranks where to recruit next.

The platform is advisory by design: every alert is reviewed by a person, every prediction carries plain-language reasons (SHAP), and the language-model copilot only narrates numbers that were verified, with a template fallback when no API key is set. All data in this repository is **synthetic**; reported metrics demonstrate the method, not real-world accuracy.

## Key Features

### Area Manager / District Officer

* **Liquidity Risk Ranking:** Ranks every agent by calibrated probability of running out of cash or e-float in the next 24 hours, using hourly P10/P50/P90 LightGBM forecasts and a fitted calibration factor.
* **Top-Up Advice with Reasons:** Recommends how much cash or e-float to add and explains the top drivers (for example the Eid effect) as SHAP-based sentences in English and Bangla.
* **Cash Delivery Route Planner:** Selects agents by chance of running out multiplied by shortfall within the van's capacity, orders stops nearest-first, warns when a stop arrives after the agent runs out, and explains an empty plan.
* **Agent Performance Insights:** Compares each agent with similar agents to flag declining, emerging, top-performing and service-gap agents, with a 0 to 100 score and a recommended action.
* **Churn Early Warning:** Predicts which active agents will go quiet within 4 weeks, with SHAP-based reasons and a suggested action.
* **Coverage Map:** Shows H3 hexagons coloured by gap type (no coverage, under-served, capacity gap, balanced, over-supplied, low demand) and ranks where to recruit, using town demand weighted by 2022 census population.
* **AI Copilot:** Writes a morning brief with drill-down links and answers questions through six read-only tools, using Gemini when a key is set and verified templates otherwise.

### Agent

* **My Cash and E-float Status:** Shows the agent's own balances, expected run-out time and advice in English or Bangla.
* **24-Hour Outlook:** Charts the projected balance for the next day, including the bad-day case below the out-of-money line.
* **Why This Forecast:** Lists the biggest reasons behind the forecast in plain words.
* **My Performance:** Shows how the agent compares with similar agents, based on volume, growth, service level and consistency.

### Risk Analyst

* **Anomaly Alert Queue:** Flags agents behaving unusually against their own history and against similar agents, using an Isolation Forest over eight behaviour signals, with the top reasons for each alert.
* **Human Review Loop:** Lets an analyst confirm or dismiss each alert with a note, recording the logged-in user in the review table, an append-only label log and an audit log.
* **AI Alert Narratives:** Generates a written explanation for any alert through Gemini, or a template when no key is configured, and labels which one wrote it.
* **Model Quality Report:** Presents held-out metrics, the policy simulation at matched liquidity, and an urban/rural fairness table.

### Platform

* **Role-Based Dashboard:** Returns a different set of panels for managers, agents and analysts from a single `/dashboard` endpoint.
* **Secure Sessions:** Uses JWT access tokens, single-use rotating refresh tokens with reuse detection, bcrypt password hashing, account lockout, and httpOnly cookies that page scripts cannot read.
* **Bilingual Interface:** Switches advice, reasons and the morning brief between English and Bangla.
* **Reproducible Data and Schema:** Generates 2M rows of synthetic hourly data with Eid, Ramadan, salary-week and rain effects, and manages the schema with checksum-protected versioned SQL migrations.
* **Interactive API Docs:** Exposes 33 documented endpoints through FastAPI's OpenAPI interface at `/docs`.

## Project Structure

```text
.
├── docker-compose.yml            # db, seed (one-off), backend, frontend
├── backend/                      # FastAPI + PostgreSQL + ML
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example              # copy to .env before running
│   ├── artifacts/                # trained models, calibration, metrics (shared volume)
│   ├── app/
│   │   ├── main.py               # app start-up: migrations, pool, data store, services
│   │   ├── api/                  # routers: core, auth, dashboard, intel, coverage, copilot
│   │   ├── auth/                 # JWT, bcrypt, role dependencies, user repository
│   │   ├── core/                 # settings, constants, JSON-safe helpers
│   │   ├── data/                 # synthetic generator, calendar (Eid/Ramadan), 38-town census table
│   │   ├── db/                   # asyncpg pool, queries, migration runner
│   │   │   └── migrations/       # 0001 core data ... 0004 users and refresh tokens
│   │   ├── ml/                   # forecasting, liquidity maths, SHAP, anomaly, churn,
│   │   │                         #   performance, coverage, rebalance, simulation
│   │   └── services/             # liquidity, anomaly, copilot, coverage, dashboard, LLM
│   └── scripts/                  # docker_seed.sh, migrate, generate_data, train*, create_user,
│                                 #   verify_anomaly, smoke_test*
└── frontend/                     # Next.js 16 (App Router, server components)
    ├── Dockerfile
    ├── package.json
    ├── scripts/copy-map-worker.mjs   # copies MapLibre worker files into public/
    └── src/
        ├── proxy.ts              # login check + silent token renewal on every request
        ├── app/
        │   ├── (auth)/login/
        │   └── (app)/            # dashboard, risk, agents/[code], route, alerts,
        │                         #   insights, coverage, copilot, models
        ├── actions/              # Server Actions: login, review alert, ask copilot
        ├── components/           # ui, layout, charts, map, dashboard, alerts, copilot
        ├── lib/api/              # client.ts: the only code that talks to the backend
        ├── services/             # one typed function per backend endpoint
        ├── store/                # Zustand: language and menu state
        └── types/
```

## Environment Setup (Docker)

### Prerequisites

* Docker Desktop, or Docker Engine with the Compose plugin (the `docker compose` command)
* Free ports **3000** (web app), **8000** (API) and **5434** (PostgreSQL)
* Git

### Services

| Service | Image / build | Host port | Role |
| --- | --- | --- | --- |
| `db` | `postgres:16` | 5434 | PostgreSQL. User `upay`, password `upay`, database `upay_pulse`, data kept in the `pgdata` volume |
| `seed` | `./backend` | none | One-off job that prepares the database and writes trained models to `./backend/artifacts` (`restart: "no"`) |
| `backend` | `./backend` | 8000 | FastAPI service, healthy once `/openapi.json` responds (up to 90 s start period) |
| `frontend` | `./frontend` | 3000 | Next.js web app, started after the backend is healthy |

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd <your-repository-folder>
```

### 2. Configure the backend environment

The compose file reads `./backend/.env` for both the `seed` and `backend` services, so the file must exist.

```bash
cp backend/.env.example backend/.env
```

Generate a secret and paste it into `JWT_SECRET`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

#### Backend variables (`backend/.env`)

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `JWT_SECRET` | **Yes** | `change-me-to-a-long-random-string` | Signs login tokens. Replace it with a long random value |
| `GOOGLE_API_KEY` | No | none | Enables Gemini for the copilot and alert narratives. Without it the app uses labelled templates |
| `GEMINI_MODEL` | No | `gemini-flash-latest` | Gemini model name used through LangChain |
| `ACCESS_TOKEN_MINUTES` | No | `60` | Access-token lifetime. Raise it for long demos |
| `REFRESH_TOKEN_DAYS` | No | `7` | Refresh-token lifetime. Keep `SESSION_DAYS` on the frontend equal to it |
| `DEMO_AS_OF` | No | `2026-05-20 08:00` | The demo clock. `2026-05-18 08:00` gives a calmer risk mix |
| `N_AGENTS`, `START_DATE`, `END_DATE` | No | `300`, `2025-05-01`, `2026-06-30` | Size and span of the synthetic dataset |
| `TEST_DAYS`, `VAL_DAYS`, `TRAIN_SAMPLE_FRAC` | No | `60`, `30`, `0.5` | Time split and training sample used by the models |
| `APP_ENV` | No | `dev` | Environment name |

`DATABASE_URL`, `AUTO_MIGRATE` and `CORS_ORIGINS` appear in `.env.example` but **docker-compose.yml overrides them** (`postgresql://upay:upay@db:5432/upay_pulse`, `true` and `http://localhost:3000`), so you do not need to change them for Docker.

#### Frontend variables (set in `docker-compose.yml`)

| Variable | Value in compose | Purpose |
| --- | --- | --- |
| `API_BASE_URL` | `http://backend:8000` | Backend address, used only on the server and never sent to the browser |
| `COOKIE_SECURE` | `"false"` | Set to `"true"` when the site is served over HTTPS |
| `SESSION_DAYS` | `"7"` | Refresh-cookie lifetime. Match `REFRESH_TOKEN_DAYS` |
| `NEXT_PUBLIC_SHOW_DEMO_LOGINS` | `"true"` (build arg) | Shows the demo-account buttons. Set `"false"` for anything public |
| `NEXT_PUBLIC_MAP_STYLE` | not set (optional build arg) | Empty uses the light CARTO basemap, `blank` gives a plain offline background |

`NEXT_PUBLIC_*` values are baked into the image at build time, so rebuild the frontend after changing them.

### 3. Start the database

```bash
docker compose up -d db
docker compose ps
```

Wait until `upay_pulse_db` shows `healthy`.

### 4. Seed the data and train the models (one-off)

The API loads the trained models and the dataset when it starts, so run the seed job to completion before starting the backend. It can take several minutes.

```bash
docker compose up --build seed
```

The command returns when the job ends. Trained artifacts are written to `./backend/artifacts`, so later runs reuse them.

### 5. Start the backend and frontend

```bash
docker compose up -d --build backend frontend
docker compose ps
```

The backend reports `healthy` once `/openapi.json` responds, and the frontend starts after that.

### 6. Open the application

| What | URL |
| --- | --- |
| Web app | http://localhost:3000 |
| API documentation (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| PostgreSQL from your machine | `postgresql://upay:upay@localhost:5434/upay_pulse` |

Sign in with a demo account (password **`Pulse@2026`**):

| Username | Role | Sees |
| --- | --- | --- |
| `manager` | Area manager | All districts |
| `dso_sylhet` | District officer | Sylhet |
| `agent_ag0142` | Agent | Agent AG0142 only |
| `analyst` | Risk analyst | Alerts, review activity and model quality |

If login reports that the user does not exist, create the demo accounts:

```bash
docker compose run --rm backend python3 -m scripts.create_user demo
```

### Running the seed steps manually (optional)

If you prefer to run the preparation yourself, or want to re-run one step, use the same container:

```bash
docker compose run --rm seed python3 -m scripts.migrate up
docker compose run --rm seed python3 -m scripts.generate_data
docker compose run --rm seed python3 -m scripts.train
docker compose run --rm seed python3 -m scripts.build_agent_weekly
docker compose run --rm seed python3 -m scripts.train_churn
docker compose run --rm seed python3 -m scripts.create_user demo
```

### Useful commands

```bash
# Follow logs
docker compose logs -f backend
docker compose logs -f frontend

# Retrain only the anomaly detector, then check the fix (prints PASS or FAIL)
docker compose run --rm seed python3 -m scripts.train_anomaly
docker compose run --rm seed python3 -m scripts.verify_anomaly

# Backend smoke tests
docker compose run --rm seed python3 -m scripts.smoke_test

# Restart the API after retraining models
docker compose restart backend

# Stop everything (keeps the database volume)
docker compose down

# Full reset: also deletes the database volume. Delete ./backend/artifacts to retrain from scratch
docker compose down -v
```

### Troubleshooting

| Symptom | Fix |
| --- | --- |
| `env file ./backend/.env not found` | Run `cp backend/.env.example backend/.env` |
| Backend is unhealthy or exits at start-up | The seed has not finished or failed. Check `docker compose logs seed`, then run `docker compose restart backend` |
| Port already in use | Stop the other service, or change the left-hand side of the port mapping in `docker-compose.yml` |
| Login fails after a clean database | Create the demo users with the `create_user demo` command above |
| "Too many failed attempts" | Wait 15 minutes, or run `docker compose run --rm backend python3 -m scripts.create_user unlock --username manager` |
| Map shows hexagons on a plain background | The basemap needs internet access. Offline, this is expected, and the data still renders |
| Changed `NEXT_PUBLIC_*` but nothing changed | Rebuild: `docker compose up -d --build frontend` |