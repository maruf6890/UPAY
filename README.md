# upay Pulse: Agent Liquidity Intelligence










\

**upay Pulse** is an AI-powered liquidity intelligence platform for mobile-money agent networks.

It helps district and area managers:

* Predict which agents may run out of **cash or e-float** within the next 24 hours.
* Recommend **how much liquidity to deliver**.
* Prioritize agents for a **cash-delivery route**.
* Detect **unusual, declining, or potentially departing agents**.
* Identify **coverage and recruitment gaps**.
* Explain recommendations in **English and Bangla**.
* Investigate alerts through an **AI-assisted analyst workflow**.

The project was built for the **DIU CPC × upay AI Hackathon 2026 — Track 05** and uses a reproducible synthetic dataset containing **300 agents**.

> **Important:** All data in this repository is synthetic. Reported metrics demonstrate the methodology and implementation, not real-world production accuracy.

---

<!-- Banner Image (Usually at the very top of the README) -->
![upay Pulse Banner](ss/banner.png)

## Overview

A mobile-money agent typically manages two balances:

* **Physical cash**
* **Digital e-float**

If either balance reaches zero during business hours, the agent may be unable to serve customers. This can result in lost transactions for both the agent and the operator.

upay Pulse moves this decision **from reactive monitoring to proactive planning**.

### How it works

1. A pooled **LightGBM quantile model** forecasts hourly net cash flow.
2. The model produces **P10, P50, and P90** scenarios representing different demand conditions.
3. A calibration layer converts the forecasts into:

   * Stockout probability
   * Expected run-out time
   * Recommended top-up amount
4. A route planner determines which agents a cash van should visit and in what order.
5. Additional ML modules detect:

   * Behavioral anomalies
   * Churn risk
   * Performance changes
   * Geographic coverage gaps
6. **SHAP explanations** provide human-readable reasons behind model predictions.
7. The **AI Copilot** summarizes verified results and provides drill-down links.

The platform is advisory by design: recommendations are reviewed by humans before action. The AI layer only narrates verified data and falls back to deterministic templates when no Gemini API key is configured.

---

# Key Features

## 1. Area Manager / District Officer

### Liquidity Risk Ranking

Ranks agents according to their calibrated probability of running out of:

* Cash
* E-float

The ranking uses hourly **P10/P50/P90 LightGBM forecasts** and a fitted calibration factor.

### Top-Up Advice

Recommends how much liquidity should be added to an agent.

Each recommendation includes human-readable reasons, such as:

* Recent transaction volume
* Expected demand
* Historical behavior
* Eid effects
* Other important model drivers

Reasons are generated using SHAP and are available in both **English and Bangla**.

### Cash Delivery Route Planner

Creates a prioritized delivery route based on:

* Probability of stockout
* Expected liquidity shortfall
* Van capacity
* Agent location

The planner prioritizes high-risk agents and orders stops using proximity.

It also warns when a planned stop may be reached **after the predicted run-out time**.

### Agent Performance Insights

Compares agents with similar agents and identifies:

* Declining agents
* Emerging agents
* Top performers
* Service gaps

Each agent receives a **0–100 performance score** and a recommended action.

### Churn Early Warning

Predicts which active agents are likely to become inactive within approximately four weeks.

The system provides:

* Churn risk
* SHAP-based reasons
* Suggested action

### Coverage Map

Uses **H3 hexagons** to visualize geographic coverage.

Coverage areas are classified as:

* No coverage
* Under-served
* Capacity gap
* Balanced
* Over-supplied
* Low demand

Recruitment opportunities are ranked using town demand weighted by **2022 census population**.

### AI Copilot

Provides a manager-facing AI assistant that can:

* Generate a morning brief
* Summarize important risks
* Explain recommendations
* Answer operational questions
* Provide drill-down links to detailed endpoints

The Copilot uses Gemini when configured and falls back to verified templates when an API key is unavailable.

---

# 2. Agent Dashboard

Agents receive a simplified view focused on their own liquidity and performance.

### My Cash & E-Float Status

Shows:

* Current cash balance
* Current e-float balance
* Expected run-out time
* Recommended action

Available in **English and Bangla**.

### 24-Hour Outlook

Displays projected balances for the next 24 hours, including a bad-day scenario showing when the balance may cross the out-of-money threshold.

### Why This Forecast?

Explains the main factors contributing to the liquidity forecast in plain language.

### My Performance

Shows how the agent compares with similar agents based on:

* Transaction volume
* Growth
* Service level
* Consistency

---

# 3. Risk Analyst

### Anomaly Alert Queue

Detects unusual agent behavior using an **Isolation Forest** over eight behavioral signals.

Alerts include the most important reasons behind the anomaly.

### Human Review Loop

Analysts can:

* Confirm an alert
* Dismiss an alert
* Add a review note

Reviews are recorded with:

* Logged-in analyst
* Append-only label history
* Audit log

### AI Alert Narratives

Generates human-readable explanations for anomaly alerts using Gemini.

If Gemini is unavailable, the system uses a deterministic template.

The interface clearly identifies which mechanism generated the explanation.

### Model Quality Report

Provides:

* Held-out model metrics
* Liquidity policy simulation
* Matched-liquidity comparison
* Urban/rural fairness analysis

---

# 4. Platform

### Role-Based Dashboard

A single `/dashboard` endpoint provides different dashboard capabilities depending on the authenticated user's role.

Supported roles include:

* Area Manager
* District Officer
* Agent
* Risk Analyst

### Secure Authentication

The platform uses:

* JWT access tokens
* Single-use rotating refresh tokens
* Refresh-token reuse detection
* bcrypt password hashing
* Account lockout
* `httpOnly` cookies

<!-- Copilot Service Flow -->
### OVERVIEW OF COPILOT SERVICE
![Copilot Service](ss/copilot_service.jpeg)

<!-- Demand Distribution Graph -->
### DEMAND DISTRIBUTION ACROSS THE COUNTRY
![Demand Distribution](ss/demeand_distribution.png)


### Reproducible Synthetic Dataset

The project generates approximately **2 million rows** of synthetic hourly data with factors including:

* Eid
* Ramadan
* Salary weeks
* Rain
* Agent behavior
* Transaction activity

Database changes are managed using checksum-protected versioned SQL migrations.

### API Documentation

FastAPI exposes **33 documented endpoints** through OpenAPI/Swagger.

---

# Architecture

<!-- Architecture Diagram -->
![Architecture Diagram](ss/architecture.jpeg)

---

# Project Structure

```text
.
├── docker-compose.yml

├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   │
│   ├── artifacts/
│   │   └── trained models, calibration and metrics
│   │
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   └── core, auth, dashboard, intel,
│   │   │      coverage and copilot routers
│   │   │
│   │   ├── auth/
│   │   │   └── JWT, bcrypt, roles and user repository
│   │   │
│   │   ├── core/
│   │   │   └── settings, constants and helpers
│   │   │
│   │   ├── data/
│   │   │   └── synthetic data, calendar and census data
│   │   │
│   │   ├── db/
│   │   │   ├── asyncpg pool
│   │   │   ├── queries
│   │   │   └── migrations/
│   │   │
│   │   ├── ml/
│   │   │   ├── forecasting
│   │   │   ├── liquidity
│   │   │   ├── SHAP
│   │   │   ├── anomaly detection
│   │   │   ├── churn
│   │   │   ├── performance
│   │   │   ├── coverage
│   │   │   ├── rebalancing
│   │   │   └── simulation
│   │   │
│   │   └── services/
│   │       ├── liquidity
│   │       ├── anomaly
│   │       ├── copilot
│   │       ├── coverage
│   │       ├── dashboard
│   │       └── LLM
│   │
│   └── scripts/
│       ├── docker_seed.sh
│       ├── migrate
│       ├── generate_data
│       ├── train*
│       ├── create_user
│       ├── verify_anomaly
│       └── smoke_test*
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── scripts/
    │   └── copy-map-worker.mjs
    │
    └── src/
        ├── proxy.ts
        │
        ├── app/
        │   ├── (auth)/login/
        │   └── (app)/
        │       ├── dashboard
        │       ├── risk
        │       ├── agents/[code]
        │       ├── route
        │       ├── alerts
        │       ├── insights
        │       ├── coverage
        │       ├── copilot
        │       └── models
        │
        ├── actions/
        │   ├── login
        │   ├── review alert
        │   └── ask copilot
        │
        ├── components/
        │   ├── ui
        │   ├── layout
        │   ├── charts
        │   ├── map
        │   ├── dashboard
        │   ├── alerts
        │   └── copilot
        │
        ├── lib/api/
        │   └── client.ts
        │
        ├── services/
        │   └── typed backend functions
        │
        ├── store/
        │   └── Zustand state
        │
        └── types/
```

## Live Deployment

The latest deployed version of **upay Pulse** is available online. The frontend communicates directly with the deployed backend through the configured production API URL.

| Service | URL |
|---|---|
| **Frontend** | [https://upay-8fju.onrender.com/login](https://upay-8fju.onrender.com/login) |
| **Backend API** | [https://upay-backend-ywmk.onrender.com/](https://upay-backend-ywmk.onrender.com/) |
| **API Documentation** | [https://upay-backend-ywmk.onrender.com/docs](https://upay-backend-ywmk.onrender.com/docs) |
| **API Health Check** | [https://upay-backend-ywmk.onrender.com/health](https://upay-backend-ywmk.onrender.com/health) |

---

## Local Development

For local development, the application is containerized and managed using **Docker Compose**, which provisions the frontend, backend, and PostgreSQL database automatically.

### Starting the Application

To build and start the complete application locally, run the following command from the root directory:

```bash
docker compose up -d --build
```

### Local Services

Once the containers are successfully running, the local services will be accessible at the following endpoints:

| Service | URL / Connection String |
|---|---|
| **Frontend** | [http://localhost:3000](http://localhost:3000) |
| **Backend API** | [http://localhost:8000](http://localhost:8000) |
| **API Documentation (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Health Check** | [http://localhost:8000/health](http://localhost:8000/health) |
| **PostgreSQL Database** | `postgresql://upay:upay@localhost:5434/upay_pulse` |

# Getting Started

## Prerequisites

Make sure the following are installed:

* Docker Desktop **or** Docker Engine with the Compose plugin
* Git
* Free port **3000** for the frontend
* Free port **8000** for the backend
* Free port **5434** for PostgreSQL

---

# Docker Setup

## 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-repository-folder>
```

---

## 2. Create the Backend Environment File

The Docker Compose configuration uses `backend/.env` for both the seed and backend services.

Create it from the example:

```bash
cp backend/.env.example backend/.env
```

---

## 3. Generate a JWT Secret

Generate a secure secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into:

```env
JWT_SECRET=<your-generated-secret>
```

---

# Environment Variables

## Backend

The main backend environment variables are:

| Variable               | Required | Default               | Purpose                                         |
| ---------------------- | -------- | --------------------- | ----------------------------------------------- |
| `JWT_SECRET`           | **Yes**  | —                     | Secret used to sign authentication tokens       |
| `GOOGLE_API_KEY`       | No       | —                     | Enables Gemini for Copilot and alert narratives |
| `GEMINI_MODEL`         | No       | `gemini-flash-latest` | Gemini model used through LangChain             |
| `ACCESS_TOKEN_MINUTES` | No       | `60`                  | Access-token lifetime                           |
| `REFRESH_TOKEN_DAYS`   | No       | `7`                   | Refresh-token lifetime                          |
| `DEMO_AS_OF`           | No       | `2026-05-20 08:00`    | Demo clock                                      |
| `N_AGENTS`             | No       | `300`                 | Number of synthetic agents                      |
| `START_DATE`           | No       | `2025-05-01`          | Dataset start date                              |
| `END_DATE`             | No       | `2026-06-30`          | Dataset end date                                |
| `TEST_DAYS`            | No       | `60`                  | Test period                                     |
| `VAL_DAYS`             | No       | `30`                  | Validation period                               |
| `TRAIN_SAMPLE_FRAC`    | No       | `0.5`                 | Training sample fraction                        |
| `APP_ENV`              | No       | `dev`                 | Application environment                         |

For Docker, `DATABASE_URL`, `AUTO_MIGRATE`, and `CORS_ORIGINS` are overridden by `docker-compose.yml`.

Therefore, they normally do not need to be changed for local Docker development.

---

## Frontend

The frontend variables are configured through `docker-compose.yml`.

| Variable                       | Value                 | Purpose                            |
| ------------------------------ | --------------------- | ---------------------------------- |
| `API_BASE_URL`                 | `http://backend:8000` | Backend address used by the server |
| `COOKIE_SECURE`                | `false`               | Set to `true` when using HTTPS     |
| `SESSION_DAYS`                 | `7`                   | Refresh-cookie lifetime            |
| `NEXT_PUBLIC_SHOW_DEMO_LOGINS` | `true`                | Shows demo login buttons           |
| `NEXT_PUBLIC_MAP_STYLE`        | Optional              | Controls the MapLibre basemap      |

> `NEXT_PUBLIC_*` variables are baked into the frontend image during build time. Rebuild the frontend after changing them.




```text
backend/artifacts/
```

These artifacts can be reused by later backend runs.

---

# 6. Start the Backend and Frontend and Database with Docker

Once the seed job completes:

```bash
docker compose up -d
```

Check all services:

```bash
docker compose ps
```

You should see:

```text
db
backend
frontend
```

The backend becomes healthy when:

```text
/openapi.json
```

is available.

The frontend starts after the backend becomes healthy.

---

# 7. Verify the Deployment

Check running containers:

```bash
docker ps
```

Check backend logs if necessary:

```bash
docker compose logs backend
```

Check frontend logs:

```bash
docker compose logs frontend
```

---

# 8. Open the Application

| Service            | URL                                                |
| ------------------ | -------------------------------------------------- |
| Web application    | http://localhost:3000                              |
| Swagger / API Docs | http://localhost:8000/docs                         |
| Health check       | http://localhost:8000/health                       |
| PostgreSQL         | `postgresql://upay:upay@localhost:5434/upay_pulse` |

---

# Demo Accounts

The default demo password is:

```text
Pulse@2026
```

| Username       | Role             | Access                            |
| -------------- | ---------------- | --------------------------------- |
| `manager`      | Area Manager     | All districts                     |
| `dso_sylhet`   | District Officer | Sylhet                            |
| `agent_ag0142` | Agent            | Agent AG0142 only                 |
| `analyst`      | Risk Analyst     | Alerts, reviews and model quality |

---

# Manual Backend Setup

Docker is the recommended way to run the complete application.

If you want to run the backend manually, use a Python virtual environment.

## 1. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it:

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Run Database Migrations

```bash
python -m scripts.migrate up
```

---

## 4. Generate Synthetic Data

```bash
python -m scripts.generate_data
```

---

## 5. Train the Models

```bash
python -m scripts.train
```

---

## 6. Build Agent Weekly Features

```bash
python -m scripts.build_agent_weekly
```

---

## 7. Train the Churn Model

```bash
python -m scripts.train_churn
```

---

## 8. Create Demo Users

```bash
python -m scripts.create_user demo
```

---

# Troubleshooting

| Problem                                     | Solution                                                                                     |
| ------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `env file ./backend/.env not found`         | Run `cp backend/.env.example backend/.env`                                                   |
| Backend is unhealthy                        | Check whether the seed job completed successfully                                            |
| Seed failed                                 | Run `docker compose logs seed`                                                               |
| Backend exits during startup                | Make sure the database and model artifacts are ready                                         |
| Port already in use                         | Stop the service using the port or change the host-side port mapping in `docker-compose.yml` |
| Login fails after a clean database          | Run the demo-user creation command                                                           |
| `Too many failed attempts`                  | Wait 15 minutes or unlock the user manually                                                  |
| Map shows hexagons on a plain background    | The basemap requires internet access; the map data itself still works offline                |
| Changed `NEXT_PUBLIC_*` but nothing changed | Rebuild the frontend image                                                                   |


---

# Development Workflow

A typical development workflow is:

```text
Clone repository
      │
      ▼
Create backend/.env
      │
      ▼
Start PostgreSQL
      │
      ▼
Run seed job
      │
      ├── Generate synthetic data
      ├── Run migrations
      └── Train ML models
      │
      ▼
Start backend
      │
      ▼
Backend health check
      │
      ▼
Start frontend
      │
      ▼
Open http://localhost:3000
```

---

# Technology Stack

## Backend

* Python 3.12
* FastAPI
* PostgreSQL 16
* asyncpg
* LightGBM
* scikit-learn
* SHAP
* LangChain
* Gemini

## Frontend

* Next.js 16
* React 19
* TypeScript
* Tailwind CSS 4
* Zustand
* MapLibre GL

## Infrastructure

* Docker
* Docker Compose
* PostgreSQL
* OpenAPI / Swagger

---

# Important Notes

* The dataset is **fully synthetic**.
* Model metrics should not be interpreted as production performance.
* The platform is designed as a **decision-support system**, not an autonomous decision-maker.
* Human review remains part of the anomaly-management workflow.
* AI-generated explanations are grounded in verified application data.
* When Gemini is unavailable, deterministic templates are used instead.
* The Docker seed job should complete successfully before relying on the backend's trained model artifacts.
