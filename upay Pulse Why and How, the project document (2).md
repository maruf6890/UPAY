# upay Pulse: Agent Liquidity Intelligence for Mobile-Money Networks

Oct 4, 2026 **·`@Mehedi_Hassan_Maruf`  `@iftakhar_Hossain_Sami` `@Nasim_Khan_milon**`

Context: DIU CPC × upay AI Hackathon 2026, Track 05, AI for liquidity management in a mobile-financial-services agent network; written for operations leaders and technical judges.

## 1. Project Title & Elevator Pitch

**Project name:** **upay Pulse**, Agent Liquidity Intelligence. The name is final and is used in the web app, the API and this document.

**Elevator pitch:** upay Pulse predicts, a day ahead, which mobile-money agents will run out of cash or e-float, tells the district manager exactly how much to deliver and in what order, and explains every recommendation in plain English and Bangla. On a 60-day held-out synthetic test it produced about **36% fewer stockout hours at the same average cash held**, and the same platform flags suspicious agents, warns a median **3 weeks ahead** of agents about to go quiet, and ranks where to recruit next.

## 2. The "Why": Problem Statement & Motivation

### The status quo

A mobile-money agent is a small shop that holds two balances: physical **cash** and digital **e-float**. Cash-out customers drain the cash drawer; cash-in customers drain the e-float. When either balance reaches zero during an open hour, the customer is turned away, the agent loses commission, and the operator loses transaction volume.

Liquidity is managed reactively. Agents call when they are empty, and the district officer's cash van follows habitual rounds. In our simulation this **habitual plan** is the baseline to beat: it produced **34,985 stockout agent-hours** over the 60-day test at the same average cash that our plan held.

### The pain points

- **Demand is not stationary.** Eid, Ramadan, salary week, remittance peaks and rain push hourly cash flow far from any trailing average. A 7-day same-hour average is **25% worse** on hourly error and **53% worse** on daily net-flow error than our model.
- **Risk is two-sided and lives in the tails.** An agent can run dry of cash or of e-float, and a point forecast hides the bad day that actually causes the stockout. The system must forecast **quantiles**, not averages.
- **Idle cash is a cost too.** Padding every agent "to be safe" ties up capital. At equal coverage, our model needs a **22% smaller safety buffer** than the 7-day baseline.
- **One van, many agents.** A district officer cannot visit everyone. The real question is whom first, inside a cash capacity; for Dhaka at the default settings the answer is **12 stops, ৳4.4M carried, 81 km**.
- **Fraud and attrition hide in aggregate volume.** Structuring just under the **৳50,000** reporting threshold, off-hours bursts, fake cash-ins and velocity spikes sit inside normal totals, and agents drift away weeks before anyone notices.
- **Recruiting runs on intuition.** There is no systematic view of where agents are missing or where existing agents keep running out of cash.
- **Black-box scores do not get acted on.** A district officer needs the reason in plain words, in their own language.

### The motivation

- **Why now:** the operator already owns the right data, hourly transactions and balances per agent. Gradient-boosted quantile models are fast enough to retrain on a single machine, and LLMs can finally narrate results in Bangla, provided they are fenced in.
- **Why our approach:** we optimise **decisions, not forecast scores**. The headline result is measured by a policy simulation at matched liquidity, not by error alone. Every prediction ships with SHAP-based reasons in English and Bangla, every alert goes to a human whose decision is stored as a label, and the language model only narrates numbers that were verified, with a template fallback when it is unavailable.

## 3. The "What": High-Level Solution

upay Pulse is a three-layer system: a **PostgreSQL 16** data layer, an async **FastAPI** intelligence layer running five model families, and a role-aware **Next.js 16** web app. It turns raw agent transactions into five daily decisions: who needs money, how much, which route to drive, who looks suspicious, and where the network should grow.

### The four core features

| Feature | What it does | Pain point it removes | Evidence (synthetic data) |
| --- | --- | --- | --- |
| **Liquidity Engine** | LightGBM predicts hourly net cash flow as a low, middle and bad-day case; calibrated cumulative bands give the chance of running out, the expected run-out hour and a top-up for cash or e-float, with SHAP reasons in English and Bangla | Non-stationary demand, two-sided tail risk, idle cash | Hourly error **25%** lower, daily error **53%** lower, buffer **22%** smaller, **36%** fewer stockout hours at matched liquidity |
| **Cash Route Planner** | Picks agents by chance of running out × shortfall until the van is full, orders stops nearest-first (30 km/h plus 10 minutes a stop), warns when a stop arrives after the agent has run out, and explains an empty plan | One van, many agents | Dhaka default: **12 stops, ৳4.4M, 81 km** |
| **Risk and Integrity Monitor** | Isolation Forest on 8 behaviour signals, each compared with the agent's own history and with similar agents; every alert carries its top reasons; analysts confirm or dismiss and every decision is stored as a label | Fraud and anomalies hidden in volume | AUC **0.945**, all **12 of 12** planted episodes caught, precision 24%, recall 55%, 2.8 false alerts a day |
| **Network Intelligence** | Performance flags and score against similar agents, a 4-week churn warning with reasons, and an H3 hexagon coverage map that ranks where to recruit | Silent attrition, recruiting by intuition | Churn AUC **0.94**, **16 of 16** test churners warned a median **3 weeks** early; **304** hexagons ranked |

### Cross-cutting layer

- **One dashboard, three views.** The same `/dashboard` returns different panels for an area manager, an agent and a risk analyst. An agent sees only their own balances and advice.
- **Bilingual by design.** Advice, reasons and the morning brief switch between English and Bangla.
- **Copilot.** A five-section morning brief with drill-down links, and a question box that can call six read-only tools. It cannot change data or contact anyone.

## 4. The "How": Deep-Dive Technical Architecture

### System architecture

```text
  People: area manager | agent | risk analyst
        |  browser
        v
  Next.js 16 web app
    proxy.ts: login check + silent token renewal
    Server Components + Server Actions
    publicApi() / privateApi()  <- the only code that talks to the backend
        |  JSON + Bearer token
        v
  FastAPI (async)   auth | dashboard | liquidity | alerts | intel | coverage | copilot   (33 endpoints)
        |
        +-- Forecast:        LightGBM P10/P50/P90 -> cumulative bands x k -> stockout chance -> top-up + SHAP reasons (EN/BN)
        +-- Detect + route:  Isolation Forest -> alerts for human review ; greedy van route
        +-- Insight + map:   performance (B4), churn (B7), H3 coverage (C1)
        +-- Copilot:         template or Gemini over 6 read-only tools
        |  asyncpg (raw SQL, COPY bulk load)
        v
  PostgreSQL 16
    agents | hourly (2M rows) | daily | agent_weekly | weather | anomaly_labels
    alert_reviews | feedback_log | audit_log | model_runs | users | refresh_tokens
```

**End-to-end flow**

1. **Ingest.** A generator builds **300 agents × 426 days × 16 open hours, about 2M hourly rows**, with Eid, Ramadan, salary-week, remittance and rain effects, then bulk-loads them with PostgreSQL `COPY`. Versioned SQL migrations (0001 to 0004) own the schema, and each is checksum-protected so an applied file cannot be silently edited.
2. **Train offline.** `scripts.train` builds the features, trains the quantile models, fits the calibration factors, runs the policy simulation and writes `artifacts/` plus a `model_runs` row. Separate scripts train the churn model and the anomaly detector.
3. **Serve online.** A request pulls a 30-day window from PostgreSQL through asyncpg, builds features, and runs inference in a worker thread so the event loop stays free. Results are cached per `as_of` hour in a small LRU cache, guarded by an async lock.
4. **Decide.** Services turn model output into a risk ranking, top-ups, a route, alerts, coverage gaps and a dashboard shaped by role.
5. **Present.** Next.js renders on the server, so the browser never sees the backend address or the token.

### Tech stack and why we chose it

| Layer | Choice | Why this over the alternative |
| --- | --- | --- |
| API | **FastAPI**, async, Python 3.12 | Native async keeps the server responsive during database reads; CPU-heavy inference is pushed to a thread. Automatic OpenAPI docs. Flask or Django would need extra work for the same concurrency |
| Data access | **Raw asyncpg**, no ORM | Explicit SQL, `COPY` bulk loading of 2M rows and streaming reads, with no hidden queries. An ORM would add overhead exactly where volume is highest |
| Database | **PostgreSQL 16** with versioned migrations | Transactional schema changes, a JSONB audit trail, a time-indexed 2M-row table. SQLite or CSV files would not give audit, concurrency or migrations |
| Forecasting | **LightGBM** quantile regression | Strong on tabular data, fast on millions of rows, and native SHAP contributions explain each forecast without a second model. Deep sequence models are slower to train and calibrate, and harder to explain per hour |
| Anomaly detection | **Isolation Forest** | Unsupervised, because real fraud labels are scarce; peer-adjusted z-scores remove market-wide moves such as Eid. A supervised classifier would need labels we do not have |
| Agent intelligence | **LightGBM** classifier plus SHAP; **KMeans** clusters | The same explainability path as the forecaster; clusters are descriptive only |
| Geospatial | **H3** hexagons plus **MapLibre GL** | Uniform cells with built-in neighbour lookups for spreading supply. Administrative boundaries have very uneven areas |
| Language model | **LangChain + Gemini** behind a template fallback | The model only narrates verified numbers and unverified priorities are dropped, so a hallucination cannot reach a decision. An LLM-first design would put it in the decision path |
| Frontend | **Next.js 16** server components, TypeScript, Tailwind 4, Zustand, Recharts | Server-side data loading keeps tokens off the client; only two functions can reach the API |
| Auth | **JWT** with bcrypt, single-use refresh tokens, httpOnly cookies | Reusing a refresh token ends every session of that user; script injection cannot read an httpOnly cookie |

### Engineering complexity: the liquidity engine

The hardest problem was turning hourly quantile forecasts into a **calibrated, decision-ready top-up**, because three constraints collide: no information leakage across 2M rows, tail risk that lives in a **cumulative path** and not in any single hour, and a requirement to prove value by **decision outcomes**, not by forecast error.

1. **Leakage-safe features.** 26 features per agent-hour, built only from information at least 24 hours old (lags and rolling statistics), plus Eid, Ramadan and salary-week calendars, weather and the agent profile. They are built in chunks so 2M rows fit in memory.
2. **Three quantile models.** LightGBM estimates P10, P50 and P90 of **net cash flow = cash out minus cash in** for each of the 16 open hours. A positive value drains cash, a negative one drains e-float. The split is by time: train, validation, then a 60-day test.
3. **From hourly quantiles to a path.** The sum of hourly P90s is not the P90 of the day's sum, so the engine accumulates hourly forecasts into a cumulative mean path and an upper band. A **calibration factor k**, fitted separately for cash and e-float on validation data, stretches the band so that reality stays under it about 9 days in 10. On the test period coverage was **84.5% for cash and 90.5% for e-float**.
4. **Risk and timing.** The balance minus a reserve is compared with the calibrated path. The engine picks the riskier side (cash or e-float), assigns HIGH, MEDIUM or LOW, and finds the first hour each path crosses the reserve, giving an expected and a bad-day run-out time.
5. **The action.** Top-up = **max(peak bad-day need + reserve − balance, 0)**, rounded to the nearest ৳100.
6. **The reason.** SHAP contributions from the median model at the peak-drain hour are grouped into 10 human themes, such as the Eid effect or recent transaction trend, and rendered as English and Bangla sentences.
7. **Proof by decision.** A policy simulation replays the 60 test days under each plan while **matching average liquidity**, so any gain comes from smarter allocation and not from holding more cash. Our plan had **22,377 stockout hours** against **34,985** for the habitual plan (**36% fewer**) and **41,519** for the 7-day average (**46% fewer**).

The engine is honest about its limits: the stockout probability is a ranking aid that tends to read low, and cash coverage falls short of the 90% target because the test window contains an Eid the model never saw in training.

The full derivations, with equations and worked numbers from this project, are in **Appendix A** at the end of this document, and a feature-by-feature specification is in Appendix B.

## 5. The Hackathon Journey: Challenges & Triumphs

### Roadblock 1: the anomaly detector could not see off-hours activity

- **Symptom.** The Isolation Forest caught **0 of 3** planted odd-hours episodes, and only **8 of 12** episodes overall (AUC 0.889).
- **First hypothesis, wrong.** We suspected the signal saturated against each agent's own history. Measured, it did not.
- **Real diagnosis.** The failure was in the **peer comparison**. Off-hours transactions are rare, so the peer spread was exactly zero on **34% of all agent-days**. One stray night transaction then read as +8 standard deviations, pinning the feature at its ceiling on **33% of normal days** against 68% of episode days. A signal that looks extreme a third of the time is not rare, so the forest learned to ignore it.
- **Fix.** A minimum spread, `MIN_LOG_SPREAD = 0.3` in log units, on the count-like signals. Normal days at the ceiling dropped to **0.0%** while real episodes stayed at 40.9%. We also shipped a shared `evaluate()`, a retrain-only script, and a `verify_anomaly` script that prints PASS or FAIL and was proven to fail on the old behaviour.
- **Result.** AUC **0.889 to 0.945**, episodes caught **8 to 12 of 12**, odd-hours **0 to 3 of 3**. Across 5 random seeds and all 21 planted episodes odd-hours was caught 5 of 5 every time, with AUC steady at 0.944 to 0.950. The cost is 0.2 more false alerts a day (2.6 to 2.8); precision stays near 24%. One caveat we state openly: we picked 0.3 after seeing test results, and the validation window held no planted episodes.

### Roadblock 2: the coverage map had no defensible demand model

- **Symptom.** Town weights were 38 hand-picked numbers. Any judge asking "why 3.0 for Dhaka?" would get a shrug.
- **Pivot.** We replaced them with one sourced rule: **weight = 3 × (town population ÷ Dhaka population) ^ 0.5**, using the 2022 census urban population for 28 of the 38 towns and a flagged 50,000 placeholder for the 10 towns under the census's 100,000 line. We tested exponents from 0.3 to 1.0: the map keeps its character up to about 0.5, and from 0.7 upward Dhaka itself becomes a top gap.
- **Self-correction.** Our first comparison put Dhaka at 1.0 for the new weights but 3.0 for the old ones, against a cut-off written in those units, which made raw population look like it collapsed the map. We caught it, redid the comparison on equal footing, and retracted the wrong numbers.
- **Result.** The new map stays close to the old one (**304** hexagons, 71 no-coverage, 50 under-served), and the sensitivity test shows what to claim: the untapped total swings between **৳3.1B and ৳22.0B** with the assumed reach, while 3 or 4 of the 5 top gap towns survive each change. So the product presents a **ranking, not a measurement**.

### Roadblock 3: defects that only a real browser finds

Basic checks passed while five problems were still hiding. We found each by running the real system: a headless browser through real interactions, and the live API against real data.

- **Blank maps.** MapLibre 6 could not start its web worker inside the Next.js bundle. A small script copies the worker files into `public/` on install, build and dev, and `setWorkerUrl` points the library at them.
- **A crashing copilot.** A `"use server"` file exported a constant, which Next.js forbids. We moved the form state into a plain module.
- **A form that rejected valid input.** The van-capacity box had `min=1` with `step=100000`, so only 5,000,001 passed and the default 5,000,000 did not. `step="any"` fixed it, and we now test by submitting the real form.
- **JSON that broke on missing times.** On a typical day **170 of 300 agents** have no run-out time. `NaT`, `pd.NA` and numpy's NaT are now handled in one `clean()` function, tested on 11 edge cases.
- **An empty route that lied.** "No stops" looked like "nobody needs cash". The API now returns a `reason` and the smallest cash need, and the page explains "the van is too small" with a one-click fix.

The outcome is a regression run of **25 page loads across three roles with no errors**, plus four backend smoke tests.

## 6. Business Impact & Viability

### Target users

| User | Job to be done | What upay Pulse gives them |
| --- | --- | --- |
| **Area manager or district officer** | Decide which agents to visit, with how much cash, in what order | A ranked risk table, top-up amounts, a van route with late-arrival warnings, and a morning brief |
| **Agent** | Know when cash or e-float will run out | Their own status, advice in English and Bangla, a 24-hour balance chart and the reasons |
| **Risk and compliance analyst** | Review unusual behaviour without drowning | An alert queue with reasons and a written explanation, plus confirm or dismiss with an audit trail |
| **Operator leadership** | Decide where to grow and who is leaving | A ranked coverage map, churn and performance views, and a model-quality page |

### Measurable impact

| Lever | Result | How it was measured | Caveat |
| --- | --- | --- | --- |
| **Stockouts avoided** | **36% fewer** stockout agent-hours (22,377 against 34,985) | 60-day policy simulation at matched average cash | Synthetic data |
| **Capital efficiency** | **22% smaller** safety buffer at equal coverage | Same held-out test against a 7-day average | Same |
| **Revenue at stake** | **৳249M a month** of volume lost to stockouts in the 300-agent network, about **৳1.2M a month** of commission at an assumed 0.5% rate | Coverage summary, 28 days to 20 May | The commission rate is a setting, not a fact |
| **Risk mitigated** | **12 of 12** planted anomaly episodes flagged; about 1 alert in 4 is a true case; 2.8 false alerts a day | Held-out test, human-review queue | Episodes were planted |
| **Retention** | **16 of 16** test churners warned a median **3 weeks** early; 0.2% false alarms (6 of 3,036 agent-weeks) | Held-out recent weeks | Churn episodes were planted as clean declines |
| **Operations** | A complete Dhaka plan in one call: **12 stops, ৳4.4M, 81 km** | Live API at default settings | A heuristic route |

We deliberately do not claim time saved, because we did not measure it.

### Why it is viable

- **Low integration cost.** It needs only hourly and daily transaction tables an operator already keeps, one PostgreSQL database and one stateless API.
- **Governance built in.** Advice is advisory. Every review is stored in `alert_reviews`, an append-only `feedback_log` and a JSON `audit_log`, and every training run is recorded with its metrics in `model_runs`.
- **Explainable by default.** Each forecast, alert and churn warning carries its top reasons, in Bangla as well as English.
- **Graceful degradation.** Without a Gemini key the copilot uses templates and labels them, so no paid service sits in the critical path.

### Validation scope and honest limits

- **All data is synthetic**, and the anomaly, churn and growth episodes were planted. The numbers prove the method works on data with known patterns; they are not a promise of real-world accuracy.
- **Fairness is uneven.** Bad-day coverage is **78.7% for rural agents** against 85.8% for urban and 91.2% for semi-urban, and this is shown on the model-quality page.
- **Role limits are a screen rule.** The API does not yet refuse a logged-in user who calls another endpoint directly.
- **Gemini has not been tested live**, and the van route orders stops nearest-first rather than by urgency; the app warns when a stop arrives too late.

## 7. Future Roadmap

With three more months we would do three things, in this order, because each one removes the biggest remaining risk to the claims above.

### 1. Prove it on real operator data

- **What.** Swap the generator for the operator's hourly history, retrain, and refit the calibration factors so cash coverage reaches the **90% target** across a full Eid cycle, where it is 84.5% today.
- **Coverage map.** Replace 38 town points and a hand-set reach with a population grid at upazila or union level, and run a **hold-out test**: hide known agents, rerun the map, and check that it finds the places they stand.
- **How we would measure it.** A pilot with matched districts, comparing stockout hours per agent-week with and without Pulse.

### 2. Time-aware, multi-van routing and gap confidence

- **What.** Replace the greedy, nearest-first route with a **vehicle-routing solver with time windows**: urgency-first ordering, several vans, and a configurable depot. In an earlier test, ordering by urgency cut late stops from about **20% to about 12%**.
- **Gap confidence.** Give every coverage gap a **stability score**: the share of plausible assumption sets in which it stays in the top 8. This answers "why should we trust this ranking?" with evidence instead of an assumption.

### 3. Close the loop and harden for production

- **Learn from reviewers.** Retrain the anomaly detector from the labels already collected in `feedback_log`, aiming to lift the **24% precision** that makes alert queues tiring.
- **Stream, don't batch.** Move from building a 30-day window on request to scheduled hourly ingestion with incremental features, plus drift monitoring on the `model_runs` history.
- **Enforce, don't suggest.** Move role and district scoping into the API, add rate limiting, and send Bangla push or SMS alerts to district officers and agents.
- **Live-test the copilot.** Run Gemini against an evaluation set that checks every number in its answers against the tool outputs.

**Quick wins in the first two weeks:** an agent search page, a churn and performance panel on the agent page, a change-password screen, and urgency-first ordering as a route option.

## Appendix A. Model Mathematics: How the Models Work Under the Hood

This appendix states each model the way a paper would: definitions first, then the estimator, then the decision rule, with a worked number from this project. Every equation matches the implementation in `app/ml/`, and where the code makes an approximation we say so.

### A.0 Notation

| Symbol | Meaning |
| --- | --- |
| a, d, h | Agent, day, and open hour within the day (h = 1 to H, with H = 16) |
| o, i | Cash-out and cash-in amounts in an hour, in BDT |
| n = o − i | Net cash flow. A positive value drains the cash drawer and raises e-float |
| s\_a | Agent scale: the agent's mean hourly gross flow (o + i) over training, at least 1 |
| y = n / s\_a | The normalised target the models learn |
| x | Feature vector, built only from information at least 24 hours old |
| τ | Quantile level, one of 0.1, 0.5, 0.9 |
| q^τ\_h | Predicted τ-quantile of the net flow in hour h, in BDT |
| z90 = 1.2816 | The 90th percentile of the standard normal distribution |
| B | Start-of-day balance (cash or e-float, as stated) |
| R | Reserve held back before an agent counts as out of money |
| k\_c, k\_f | Calibration factors for cash and e-float |
| Φ | The standard normal cumulative distribution function |

### A.1 Liquidity forecasting

**A.1.1 Target and normalisation.** The model predicts net flow, scaled by the agent's size:

```latex
n_{a,t} = o_{a,t} - i_{a,t}, \qquad y_{a,t} = \frac{n_{a,t}}{s_a}
```

Dividing by s\_a puts a village shop and a city hub on one scale. A single pooled model can then learn the shared structure (Eid, salary week, time of day) from all 300 agents, instead of 300 starved models. Predictions are multiplied back by s\_a and sorted, so the three quantiles can never cross.

**A.1.2 Quantile regression.** Each quantile minimises the pinball loss:

```latex
\rho_\tau(u) = u\,\bigl(\tau - \mathbf{1}\{u < 0\}\bigr), \qquad \hat q^{\tau}(x) = \arg\min_{f} \sum_{a,t} \rho_\tau\bigl(y_{a,t} - f(x_{a,t})\bigr)
```

The intuition is an asymmetric penalty. For τ = 0.9, under-predicting by 1 costs 0.9 and over-predicting by 1 costs 0.1, so the best prediction sits where 90% of outcomes fall below it. That is why the model captures the bad-day tail and not just the average. Gradient boosting builds the function as a sum of regression trees:

```latex
F_M(x) = \sum_{m=1}^{M} \eta\, f_m(x)
```

The settings are a learning rate η of 0.06, 63 leaves, at least 300 rows per leaf, an L2 penalty of 1.0, row and feature subsampling (0.7 and 0.8), and early stopping after 40 rounds without improvement on 100,000 validation rows. One model is trained per τ.

**A.1.3 Leakage control.** Every feature must be computable 24 hours before the hour it describes:

```latex
x_{a,t} = g\bigl(\{o_{a,u}, i_{a,u}\}_{u \le t - 24\mathrm{h}},\ \mathrm{calendar}_t,\ \mathrm{weather}_t,\ \mathrm{profile}_a\bigr)
```

In practice this means same-hour lags of 1, 2 and 7 days, a 7-day mean and standard deviation, 14-day rolling means shifted by 2 days, calendar flags (distance to Eid, Ramadan, salary week, remittance window), weather, and the agent profile. Data is split by time into train, validation (used for early stopping and for k), and a 60-day test.

**A.1.4 From hourly quantiles to a daily path.** Stockout risk lives in the cumulative drain, not in any single hour:

```latex
C_{a,h} = \sum_{j=1}^{h} n_{a,j}, \qquad m_h = \sum_{j=1}^{h} q^{0.5}_{j}
```

The hourly spreads are converted into standard deviations, and, as an approximation, accumulated as if the hours were independent:

```latex
\sigma^{+}_j = \frac{\max(q^{0.9}_j - q^{0.5}_j,\,0)}{z_{90}}, \qquad \sigma^{-}_j = \frac{\max(q^{0.5}_j - q^{0.1}_j,\,0)}{z_{90}}, \qquad \mathrm{SD}^{\pm}_h = \sqrt{\sum_{j=1}^{h} (\sigma^{\pm}_j)^2}
```

The upper bands for the cash and e-float drain are:

```latex
U^{c}_h = m_h + k_c\, z_{90}\, \mathrm{SD}^{+}_h, \qquad U^{f}_h = -m_h + k_f\, z_{90}\, \mathrm{SD}^{-}_h
```

The two obvious shortcuts fail in opposite directions. Adding the 16 hourly P90s assumes every hour goes wrong at once, which is far too conservative. Treating hours as independent under-covers, because real flows are positively correlated: an Eid day runs high all day. The factor k, fitted on validation data, corrects between the two extremes:

```latex
k^{*} = \min\Bigl\{k \in \{0.50, 0.55, \dots, 4.00\} : \tfrac{1}{N}\sum_{a,d} \mathbf{1}\bigl[P_{a,d} \le \max(\max_h U_h(k),\, 0)\bigr] \ge 0.90\Bigr\}
```

Here P is the realised peak drain of an agent-day. Cash and e-float get separate factors, and the 7-day baseline gets its own, so the comparison is fair. On the 60-day test the realised peak stayed under the bound on **84.5%** of agent-days for cash and **90.5%** for e-float. The cash shortfall is a distribution shift: the test window contains an Eid unlike any training day.

**A.1.5 Stockout probability and risk level.** For each hour the engine asks how likely the cumulative drain is to exceed the usable balance, then takes the worst hour:

```latex
p_a = \max_{h}\Bigl[\,1 - \Phi\Bigl(\frac{B - R - \mu_h}{k\,\mathrm{SD}_h}\Bigr)\Bigr]
```

For cash, μ\_h = m\_h and SD\_h = SD⁺\_h. For e-float, μ\_h = −m\_h and SD\_h = SD⁻\_h. The agent's risk side is whichever of the two gives the larger p. The level is **HIGH** if p ≥ 0.5, **MEDIUM** if p ≥ 0.2, and LOW otherwise. This is a normal approximation that ignores the correlation between hours, so p is a ranking aid that tends to read low, not a calibrated probability.

**A.1.6 Top-up and run-out hour.**

```latex
\text{need}^{*} = \max\bigl(\max_h U_h,\ 0\bigr), \qquad \text{top-up} = \max\bigl(\text{need}^{*} + R - B,\ 0\bigr)
```

The top-up is rounded to the nearest ৳100. The expected run-out hour is the first h where B − m\_h < R on the median path, and the bad-day run-out hour is the first h where B − U\_h < R. Worked example: on 20 May agent AG0142 held ৳40,560 of cash against a bad-day plan of about ৳851k, so the engine advised a top-up of **৳810,200** with a run-out around 08:00.

### A.2 Explanations: Shapley contributions

A tree ensemble F is a black box with thousands of splits. SHAP turns it into an additive explanation:

```latex
F(x) = \phi_0 + \sum_{i=1}^{p} \phi_i(x), \qquad \phi_i(x) = \sum_{S \subseteq N \setminus \{i\}} \frac{|S|!\,(p - |S| - 1)!}{p!}\,\bigl[F_{S \cup \{i\}}(x) - F_S(x)\bigr]
```

The Shapley value φ\_i is feature i's average marginal contribution over every order in which the features could be revealed, and the contributions add up exactly to the prediction. LightGBM computes them exactly for trees through `pred_contrib=True`, so no extra library or second model is needed.

For one agent-day the contributions of the median model are summed over the hours up to the peak-drain hour h\*, converted back to BDT, and grouped into 10 business themes T (Eid effect, salary week, remittance window, market day, Ramadan, weather, weekday pattern, time of day, recent trend, agent profile):

```latex
\Phi_T = s_a \sum_{h \le h^{*}} \sum_{i \in T} \phi_i(x_h)
```

For e-float the sign is flipped. The three themes with the largest |Φ\_T| become sentences in English and Bangla. For AG0142 the engine reported that the Eid effect raised the expected cash drain by about **৳201,952**, agent type and area by **৳130,107**, and the recent transaction trend by **৳126,923**. Each sentence is literally a sum of Shapley values, not a story the language model invented.

### A.3 Policy simulation and matched liquidity

Forecast error is not the goal; fewer failed customers at the same cost is. So the plans are compared inside a simulator of agent liquidity, replayed over the 60 held-out days. In each hour:

```latex
\begin{aligned}
\text{served}^{out} &= \min(o,\ \text{cash}), \qquad \text{served}^{in} = \min(i,\ \text{float}) \\
\text{short} &= (o - \text{served}^{out}) + (i - \text{served}^{in}), \qquad \text{stockout} = \mathbf{1}[\text{short} > 2000] \\
\text{cash} &\leftarrow \text{cash} - \text{served}^{out} + \text{served}^{in}, \qquad \text{float} \leftarrow \text{float} + \text{served}^{out} - \text{served}^{in}
\end{aligned}
```

A stockout hour is therefore one with more than ৳2,000 of unserved demand, roughly one failed typical transaction. Each morning the agent is reset to a plan (T^c, T^f): surplus on one side is swapped into the other, any remaining deficit is injected from outside, and excess is swept back. Three plans are compared:

- **Our plan:** the targets are the calibrated bad-day needs plus the reserve, T = (need^c\* + R, need^f\* + R).
- **7-day average:** the same rule using the baseline bands, with the baseline's own k.
- **Habitual:** a fixed target per agent, the status quo.

A plan that simply holds more cash will always have fewer stockouts, so the comparison is **matched on liquidity**. For each baseline a scale factor f in \[0.2, 6\] is found by 12 steps of bisection so that its average start-of-day liquidity equals ours:

```latex
\bar L(f \cdot T_{\text{base}}) = \bar L(T_{\text{AI}}), \qquad \bar L = \text{mean over agent-days of } (\text{cash} + \text{float}) \text{ at the start of the day}
```

At an average of about ৳525k of start-of-day liquidity per agent, our plan had **22,377** stockout agent-hours. The matched habitual plan had **34,985** (36% fewer) and the matched 7-day average had **41,519** (46% fewer). The forecast metrics behind these results are defined as:

```latex
\mathrm{MAE}_{\text{norm}} = \operatorname{mean}\frac{|y - \hat q^{0.5}|}{s_a}, \qquad \mathrm{WAPE}_{\text{daily}} = \frac{\sum_d |N_d - \hat N_d|}{\sum_d G_d}, \qquad \text{buffer reduction} = 1 - \frac{\overline{\text{need}}_{\text{AI}}}{\overline{\text{need}}_{\text{base}}}
```

where N\_d is the day's net flow, G\_d its gross flow, and the buffer comparison is made at equal coverage. These give the **25%** lower hourly error, the **53%** lower daily error and the **22%** smaller safety buffer reported in the main text.

### A.4 Anomaly detection

The detector looks for agents whose day does not look like their own past, nor like similar agents on the same day. It is unsupervised, because real fraud labels are scarce; the planted episodes are used only to measure it.

**A.4.1 Signals and two kinds of z-score.** Eight daily signals are computed per agent: transaction count, average ticket, cash-out to cash-in ratio, peak-hour share, share of transactions just under the ৳50,000 threshold, repeat-counterparty share, off-hours transactions, and round-amount share. Count-like signals are log-scaled, x ← log(1 + x). Each signal gets two standardised scores. Against the agent's own history, using the previous 28 days only (shifted one day so today is never in its own baseline):

```latex
z^{own}_{a,t} = \operatorname{clip}\Bigl(\frac{x_{a,t} - \mu_{a,t}}{\max(\sigma_{a,t},\ \varepsilon)},\ -8,\ 8\Bigr) - \operatorname{median}_{a'}\bigl(z^{own}_{a',t}\bigr)
```

The last term subtracts the same-day median over all agents, which removes market-wide moves such as Eid, a salary week or heavy rain, leaving only agent-specific change. Against similar agents (the same archetype g on the same day), using a robust median and median absolute deviation:

```latex
z^{peer}_{a,t} = \operatorname{clip}\Bigl(\frac{x_{a,t} - \operatorname{med}_{g,t}}{\max(1.4826\cdot\mathrm{MAD}_{g,t},\ \varepsilon)},\ -8,\ 8\Bigr)
```

The 8 signals times 2 scores give a 16-dimensional feature vector per agent-day.

**A.4.2 The spread floor, and why it matters.** The denominator floor is

```latex
\varepsilon = \max\bigl(f_s,\ 10^{-3}\,|\mu| + 10^{-6}\bigr), \qquad f_s = 0.3 \text{ for log-scaled signals, } 0 \text{ otherwise}
```

Off-hours transactions are usually zero, so for many peer groups the MAD is exactly 0 and the denominator collapses to about 10^-6. One stray night transaction then scores log(2) / 10^-6, far past the clip, and sits at +8 on **33% of normal agent-days**. A feature that is extreme a third of the time is not rare, so the forest cannot use it. With f\_s = 0.3 the same stray transaction scores log(2) / 0.3 ≈ **2.3σ**, while a burst of 8 off-hours transactions scores log(9) / 0.3 ≈ **7.3σ**. Ordinary noise stays ordinary and a real episode stays extreme.

**A.4.3 Isolation Forest.** The detector builds 300 random trees, each on a subsample of 4,096 agent-days. A tree splits the 16-dimensional space with a random feature and a random threshold, and unusual points are isolated in fewer splits. With h(x) the path length needed to isolate x:

```latex
s(x, n) = 2^{-\,\mathbb{E}[h(x)] / c(n)}, \qquad c(n) = 2H(n - 1) - \frac{2(n - 1)}{n}, \qquad H(i) \approx \ln i + 0.5772
```

Here c(n) is the average path length of an unsuccessful search in a binary tree, which normalises scores to (0, 1\]; values near 1 are anomalous. The day score is s, the alert score is its two-day average, and the thresholds are quantiles of the training-period scores:

```latex
A_{a,d} = \tfrac{1}{2}\bigl(s_{a,d} + s_{a,d-1}\bigr), \qquad \text{MEDIUM} = Q_{0.99}(A_{\text{train}}), \qquad \text{HIGH} = Q_{0.998}(A_{\text{train}})
```

So by construction about 1% of ordinary agent-days land in the review queue, which is why a human reviews every alert. The three signals with the largest max(|z^own|, |z^peer|) are shown as the alert's reasons.

**A.4.4 Measured result.** On the 60-day test: AUC **0.945**, all **12 of 12** planted episodes caught, precision 24%, recall 55%, 2.8 false alerts a day. Before the floor the figures were AUC 0.889 and 8 of 12 episodes.

### A.5 Churn prediction

**A.5.1 Labels.** Let T\_{a,w} be agent a's transactions in week w and b\_a the median of its first 8 weeks, its own normal. A week is inactive when activity falls below a quarter of normal, and an agent has churned at the first inactive week that is followed by another:

```latex
\text{inactive}_{a,w} = \mathbf{1}\bigl[T_{a,w} < 0.25\, b_a\bigr], \qquad e_a = \min\{w : \text{inactive}_{a,w} \wedge \text{inactive}_{a,w+1}\}
```

The prediction target for a week w in which the agent is still active, and whose outcome is already known, is whether churn happens within the next 4 weeks:

```latex
y_{a,w} = \mathbf{1}\bigl[\,w < e_a \le w + 4\,\bigr]
```

**A.5.2 Peer-adjusted features.** Raw weekly activity swings with Eid and rain, so each ratio is also divided by what similar agents did the same week:

```latex
r_{a,w} = \frac{T_{a,w} / b_a}{\operatorname{median}_{a' \in g(a)}\bigl(T_{a',w} / b_{a'}\bigr)}
```

For AG0206 in the week of 11 May the agent did 0.73 of its normal while the median similar agent did 1.09, so r = 0.73 / 1.09 = **0.68**: worse than its peers even after the holiday dip.

**A.5.3 Model.** A LightGBM classifier (200 trees, 15 leaves, learning rate 0.05) outputs a log-odds score F, and the probability is its logistic transform:

```latex
p = \sigma\bigl(F(x)\bigr) = \frac{1}{1 + e^{-F(x)}}, \qquad F(x) = \phi_0 + \sum_i \phi_i(x), \qquad \mathcal{L} = -\sum \bigl[y \log p + (1 - y)\log(1 - p)\bigr]
```

Because the SHAP contributions are in log-odds, they add up to the score exactly. For AG0206 the base was φ₀ = −7.92, a 0.04% chance for an average agent. The peer-adjusted last week added **+6.25**, the two-week trend against peers **+3.43**, being active on 6 of 7 days **+1.54**, low volatility **−0.53** and the 4-week ratio **+0.52**. With the smaller terms, F = **+3.47**, so p = 1 / (1 + e^−3.47) = **0.970**. The agent really did go quiet three weeks later.

Training and test weeks are separated by a gap equal to the horizon, so no training label looks into the test period:

```latex
w_{\text{train}} \le w_{\text{test}} - 4 - 1
```

Alerts are MEDIUM above p = 0.2 and HIGH above 0.5. On the held-out weeks the AUC was **0.94**, against 0.825 for a simple sharpest-drop rule, and average precision was 0.833 against 0.101. Of 16 test churners all 16 were warned, a median 3 weeks early, at a false-alarm rate of 0.2%.

### A.6 Agent performance scoring

Performance is always relative: each agent is compared with similar agents (the same archetype) over the same weeks, so network-wide swings do not count as growth or decline. With V the transaction value of the last four weeks and V′ that of the four before:

```latex
g_a = \frac{V_a}{V'_a} - 1, \qquad \Delta_a = g_a - \operatorname{median}_{a' \in g(a)}\, g_{a'}
```

The 0 to 100 score blends the agent's volume percentile P among its peers, its relative growth, its service level (s, the share of open hours spent out of money) and its consistency (v, week-to-week volatility):

```latex
\text{score} = 0.45\,P + 0.25\,\operatorname{clip}(50 + 100\Delta,\,0,\,100) + 0.20\cdot 100\bigl(1 - \operatorname{clip}(s/0.15,\,0,\,1)\bigr) + 0.10\cdot 100\bigl(1 - \operatorname{clip}(v/0.5,\,0,\,1)\bigr)
```

The flags are plain threshold rules on the same quantities: **DECLINING** when Δ ≤ −15%, **EMERGING** when Δ ≥ +12% and P ≥ 50, **TOP** when P ≥ 85 and not declining, and **SERVICE\_GAP** when s ≥ 8% while P ≥ 40, meaning demand is healthy but the agent keeps running dry. KMeans with 4 clusters adds a descriptive grouping only. Worked example for AG0206: Δ = −18.9% − 2.1% = −20.9% gives a growth term of 29, with P = 24 and s = 4.5%, so the score is about 0.45·24 + 0.25·29 + 0.20·70 + 0.10·60 ≈ **38**, flagged DECLINING.

### A.7 Coverage map

The map compares an estimated demand surface with measured supply on H3 hexagons of about 250 km².

**A.7.1 Demand.** Each of the 38 district towns t adds a Gaussian bell around its centre, and a hexagon c sums the bells that reach it:

```latex
D_c = \sum_{t=1}^{38} w_t \exp\Bigl(-\tfrac{1}{2}\bigl(d_{c,t} / r_t\bigr)^2\Bigr), \qquad w_t = 3\Bigl(\frac{P_t}{P_{\text{Dhaka}}}\Bigr)^{0.5}
```

Here d is the great-circle distance from the hexagon centre to the town, r\_t is the town's reach (10 to 20 km, an assumption), and P\_t is the town's 2022 census urban population. The index D has no unit, so it is converted to money by a scale κ taken from the hexagons that already hold agents, A:

```latex
\kappa = \operatorname{median}_{c \in A}\Bigl(\frac{S_c}{D_c}\Bigr), \qquad \text{demand}_c = \kappa\, D_c
```

**A.7.2 Supply.** Customers travel a few kilometres, so each agent i with 28-day volume V\_i gives half to its home hexagon and shares the other half over the six neighbours:

```latex
S_c = \sum_i V_i\Bigl[\,0.5\cdot\mathbf{1}(c = \text{home}_i) + \tfrac{0.5}{6}\cdot\mathbf{1}\bigl(c \in \text{ring}_1(\text{home}_i)\bigr)\Bigr]
```

**A.7.3 Decision rules.** With coverage ratio ρ\_c = S\_c / demand\_c, untapped volume U\_c = max(demand\_c − S\_c, 0), and u\_c the share of volume that agents inside the hexagon lose to stockouts, the first matching rule sets the type:

1. **Capacity gap:** agents inside, and u\_c ≥ max(4%, 2 × the network median of u).
2. **Low demand:** demand below 25% of the median covered hexagon, and no agent inside.
3. **No coverage:** no agent inside or in a neighbouring hexagon.
4. **Under-served:** ρ\_c < 0.5.
5. **Over-supplied:** ρ\_c > 2.0.
6. **Balanced:** none of the above.

The number of agents to recruit is U\_c divided by a typical agent's monthly volume (৳27.4M), rounded and capped at 8. Worked example for the largest gap, a hexagon near Narayanganj: D = 1.52 (Dhaka) + 0.42 (Narayanganj) + 0.07 (Gazipur) ≈ 2.03 and κ = ৳168.7M, so demand is ৳342M a month. The 36 agents that reach it supply ৳122M, so ρ = 0.36 and the hexagon is **under-served**. The shortfall of ৳220M divided by ৳27.4M gives **8 agents**.

A caution on interpretation: κ is estimated from the same agents it is used to judge, so ρ is a relative ranking and not an absolute measurement. Totals scale with κ and with the reach r, which is why they swing between ৳3.1B and ৳22.0B in the sensitivity tests while 3 or 4 of the 5 top gap towns survive each change.

### A.8 Route planning

The planner is a two-stage heuristic. Stage one selects whom to visit. Each HIGH or MEDIUM agent with a positive cash top-up T\_i gets a priority equal to its chance of running out times its shortfall, and agents are taken in descending order while they fit:

```latex
\pi_i = p_i \cdot T_i, \qquad \text{add } i \text{ if } \sum_{j \in \text{chosen}} T_j + T_i \le \text{capacity} \ \text{ and } \ |\text{chosen}| < \text{max stops}
```

This is the standard greedy rule for a knapsack problem. Stage two orders the visits from a depot at the centre of the chosen agents, always driving to the nearest unvisited stop, with distances from the haversine formula and a travel clock:

```latex
d = 2R\arcsin\sqrt{\sin^2\tfrac{\Delta\varphi}{2} + \cos\varphi_1\cos\varphi_2\sin^2\tfrac{\Delta\lambda}{2}}, \qquad t_j = t_{j-1} + \frac{d_{j-1,j}}{30\ \text{km/h}}\cdot 60 + 10\ \text{min}
```

with R = 6,371 km. If the arrival time t\_j is later than the agent's expected run-out time, the page warns that the stop comes too late. Selection costs O(n log n) and ordering O(m²) for m stops. There is no optimality guarantee: the problem with several vans and time windows is NP-hard, and ordering by urgency instead of distance is the first planned improvement. For Dhaka at the default settings the plan is 12 stops, ৳4.4M and 81 km.

### A.9 Assumptions and threats to validity

- **Hour independence.** The cumulative band adds hourly variances as if hours were independent, and the single factor k absorbs the average correlation. It cannot absorb correlation that differs between agents.
- **Normal approximation.** The stockout probability treats the cumulative drain as Gaussian and ignores correlation between hours. It is a ranking aid, not a calibrated probability.
- **Stationarity.** k is fitted on a validation period and applied later. The 84.5% cash coverage on a test window with an unseen Eid is the measured cost of that assumption.
- **Pooling.** One model serves all agents. Bad-day coverage is weaker for rural agents (78.7%) than urban (85.8%) and semi-urban (91.2%) ones.
- **Planted and synthetic evidence.** Anomaly, churn and growth episodes were injected, so AUC measures detection of designed patterns, and real fraud will be messier. The spread floor of 0.3 was chosen after seeing test results, though every floor from 0.2 to 0.5 improved on the old behaviour and 5 random seeds agreed.
- **Coverage assumptions.** Town reach, the exponent 0.5 and the 50,000 placeholder for 10 small towns are assumptions, and κ is calibrated on the agents it evaluates.

## Appendix B. Feature-by-Feature Technical Specification

Every feature is specified with the same template so they can be compared side by side: an **At a glance** table, a numbered **How it works** pipeline, the **Rules and equations** it relies on (pointing to Appendix A), its **Outputs**, and its **Safeguards and limits**. The F-numbers belong to this document; the codes B4, B7, C1 and C5 are the names used in the code and the hackathon add-ons.

### B.0 Feature index

| # | Feature | Core method | Maths | Main endpoints | Screens |
| --- | --- | --- | --- | --- | --- |
| F1 | Liquidity Engine | LightGBM quantiles, calibrated cumulative bands | A.1 to A.3 | /risk, /agents/{code}/forecast | /risk, /agents/\[code\] |
| F2 | Cash Route Planner | Greedy knapsack, then nearest neighbour | A.8 | /rebalance | /route |
| F3 | Risk and Integrity Monitor | Isolation Forest plus human review | A.4 | /alerts, /alerts/{id}/review | /alerts |
| F4 | Agent Performance (B4) | Peer-relative score and flags | A.6 | /intel/performance/\* | /insights |
| F5 | Churn Early Warning (B7) | LightGBM classifier with SHAP | A.5 | /intel/churn/\* | /insights, churn tab |
| F6 | Coverage Map (C1) | Census-weighted demand against measured supply on H3 | A.7 | /coverage/\* | /coverage |
| F7 | Copilot (C5) | Verified-number brief and a read-only tool loop | None (language layer) | /copilot/brief, /copilot/ask | /copilot |
| F8 | Access and role-aware dashboard | JWT, rotating refresh tokens, role widgets | None | /auth/\*, /dashboard | /login, /dashboard |

### B.1 F1: Liquidity Engine

| Aspect | Detail |
| --- | --- |
| **Question it answers** | Who runs out of cash or e-float in the next 24 hours, how much should they add, and why? |
| **Users** | Area manager; the agent for their own view; the analyst for model quality |
| **Reads** | `hourly` (a 30-day window), `agents`, `weather`; `artifacts/` (quantile models, agent scales, calibration factors) |
| **Writes** | Nothing at request time. Training writes `artifacts/` and a `model_runs` row |
| **Endpoints** | GET /risk, GET /agents, GET /agents/{code}/forecast, GET /meta, GET /metrics |
| **Screens** | /risk, /agents/\[code\], and the dashboard panels for liquidity overview, riskiest agents, my status, next 24 hours and why this forecast |
| **Evidence** | Hourly error 25% lower, daily error 53% lower, buffer 22% smaller, 36% fewer stockout hours at matched liquidity |

**How it works**

1. A request fixes the demo clock `as_of` (default 2026-05-20 08:00) and pulls a 30-day window from PostgreSQL, plus two days that reveal the realised outcome for the demo.
2. It builds 26 leakage-safe features for the next 16 open hours of all 300 agents and runs inference in a worker thread.
3. Three LightGBM models predict the hourly P10, P50 and P90 of net flow. The quantiles are sorted so they never cross, then scaled back to BDT.
4. The calibrated cumulative bands give a stockout probability, a risk side (cash or e-float), a level, the expected and bad-day run-out hours, and a top-up amount.
5. SHAP contributions are grouped into themes and rendered as advice in English and Bangla.
6. The result is cached per `as_of` hour (six entries, least recently used) behind an async lock, so the per-agent forecast reads the same computation as the ranking.

**Rules and equations.** See A.1.4 to A.1.6. HIGH at p ≥ 0.5, MEDIUM at p ≥ 0.2. The top-up is max(need\* + R − B, 0), rounded to ৳100, where the reserve R is a setting.

**Outputs.** Per agent: stockout probability, level, side, expected and bad-day run-out times, cash and e-float top-ups, hourly P10, P50 and P90, balance paths, the top three reasons in two languages, the advice sentence, and what the 7-day-average rule would have advised.

**Safeguards and limits**

- Features use only information at least 24 hours old, and the split is by time.
- Cash and e-float are calibrated separately, and the baseline has its own factor, so the comparison is fair.
- The probability is a ranking aid that tends to read low. Cash coverage is 84.5% against a 90% target, and rural agents are weaker (78.7%).
- On a typical day about 170 of 300 agents are LOW and have no run-out time; the API returns null for them instead of failing.

### B.2 F2: Cash Route Planner

| Aspect | Detail |
| --- | --- |
| **Question it answers** | Which agents should one van visit, in what order, carrying how much cash? |
| **Users** | Area manager or district officer |
| **Reads** | F1's risk table (HIGH and MEDIUM agents with a positive cash top-up) and agent coordinates |
| **Writes** | Nothing |
| **Endpoints** | GET /rebalance with `district`, `van_capacity_bdt` (default ৳5,000,000, must be above 0), `max_stops` (default 12) and `as_of` |
| **Screens** | /route: a map with numbered stops, the visit order, a list of agents that did not fit, and a late-arrival warning per stop |
| **Evidence** | Dhaka at the defaults: 12 stops, ৳4,436,900, 81.3 km |

**How it works**

1. Candidates are agents at HIGH or MEDIUM risk whose cash top-up is positive. Float shortfalls are digital transfers and need no visit.
2. Each candidate gets priority p × T (chance of running out times shortfall). Agents are added in descending priority while the cash fits and the stop limit allows.
3. The depot is the centre of the chosen agents. Stops are ordered nearest first by haversine distance, with a travel clock of 30 km/h plus 10 minutes per stop.
4. If nobody fits, the response says why instead of returning a bare empty list.

**Rules and equations.** See A.8. The depot, the speed and the stop time are internal settings, not API parameters.

**Outputs.** `stops` (order, agent, distance, arrival estimate, cash amount, run-out time), `total_km`, `total_cash_bdt`, `digital_transfers`, `depot`, `unserved` (the first 10 that did not fit), `reason`, `smallest_topup_bdt`, and the `van_capacity_bdt` and `max_stops` that were used.

**Safeguards and limits**

- `reason` is `van_too_small` or `no_agents_need_cash`, and the page turns the first into "your van carries ৳X but the smallest delivery needed is ৳Y" with a one-click fix. In Dhaka any capacity below ৳50,800 triggers it.
- The route orders by distance, not urgency, so the page warns when a stop arrives after the agent is expected to run out. Ordering by urgency cut late stops from about 20% to about 12% in an earlier test, and is the first planned upgrade.
- Distances are straight lines, the depot is an invented centre point, and the heuristic has no optimality guarantee.

### B.3 F3: Risk and Integrity Monitor

| Aspect | Detail |
| --- | --- |
| **Question it answers** | Which agents behave unusually against their own history and against similar agents, and what did a human decide about each? |
| **Users** | Risk analyst (primary), area manager |
| **Reads** | `daily` (the 8 behaviour signals), `agents`, `alert_reviews`; the saved Isolation Forest and its thresholds |
| **Writes** | `alert_reviews`, an append-only `feedback_log`, and a JSON `audit_log` |
| **Endpoints** | GET /alerts (status and lookback window), POST /alerts/{id}/review, GET /alerts/{id}/narrative, GET /agents/{code}/anomaly |
| **Screens** | /alerts, the anomaly chart on the agent page, and the dashboard panels for pending alerts and review activity |
| **Evidence** | AUC 0.945, all 12 of 12 planted episodes caught, precision 24%, recall 55%, 2.8 false alerts a day |

**How it works**

1. At start-up the service scores every agent-day: it builds the 16 z-score features from `daily` and applies the saved forest.
2. The queue shows each agent's latest flagged day inside the lookback window. An alert is MEDIUM above the 99th-percentile training score and HIGH above the 99.8th.
3. Each alert lists its top three signals with plain-language detail, such as "Off-hours transactions: 8 vs peer median 0".
4. The Explain button asks for a written narrative from the language model, or from a template when no key is set, and labels which one wrote it.
5. The analyst confirms or dismisses with an optional note. The reviewer is the logged-in user, never a typed name, and the decision lands in three places: the review table, the label log and the audit log.

**Rules and equations.** See A.4.1 to A.4.3: robust z-scores with the spread floor, the Isolation Forest score, a two-day average, and quantile thresholds.

**Outputs.** Alert id, agent, district, archetype, day, anomaly score, severity, up to four reasons, and the review state with reviewer, time and note.

**Safeguards and limits**

- The wording is deliberately advisory: flags for a person to check, not accusations.
- Peer adjustment and the market-wide median subtraction stop Eid or rain from raising false alerts. The spread floor stops one stray event from looking extreme.
- `scripts.verify_anomaly` prints PASS or FAIL for the fix and was proven to fail on the old behaviour.
- About three in four alerts are false positives by design of the threshold, so the queue is for review, not action. The labels in `feedback_log` are collected but not yet used to retrain the detector.

### B.4 F4: Agent Performance (B4)

| Aspect | Detail |
| --- | --- |
| **Question it answers** | Who is growing, who is declining, and who keeps running out of money despite healthy demand? |
| **Users** | Area manager and analyst; each agent sees their own standing |
| **Reads** | `agent_weekly`: 300 agents by 60 full weeks, summed from `hourly`, plus planted decline and growth episodes |
| **Writes** | Nothing at request time |
| **Endpoints** | GET /intel/weeks, /intel/performance/summary, /intel/performance/agents, /intel/performance/agents/{code}, /intel/agents/{code}/overview |
| **Screens** | /insights (Performance tab), the dashboard performance panel, and "How I compare" on the agent dashboard |
| **Evidence** | 45 of 47 declines flagged a median 2 weeks after they start; 28 of 34 growth episodes flagged a median 3 weeks after; 0.1% false DECLINING flags |

**How it works**

1. The date resolves to the latest complete week before it (20 May gives the week of 11 May). The first 8 weeks set each agent's own baseline.
2. For each week the features compare the agent with its own baseline and with the median of its archetype that same week, so a network-wide Eid dip is not counted against anyone.
3. The score blends volume percentile, relative growth, service level and consistency. Four threshold flags are then applied.
4. Each agent gets one segment, the most urgent flag, and a rule-based recommended action. KMeans adds a descriptive cluster name.
5. The summary adds up the four-week volume lost at service-gap agents.

**Rules and equations.** See A.6. On 20 May the counts were 227 steady, 36 top performers, 21 service gap, 13 declining and 3 emerging.

**Outputs.** Score, segment, flags, volume percentile, relative growth, stockout rate, lost volume over four weeks, cluster, and a 12-week series with the agent's own baseline.

**Safeguards and limits**

- Because the segment is a single label, an agent can carry more flags than its segment shows (46 top-performer flags against 36 in the segment).
- Clusters describe a group's average, so an agent can be DECLINING inside a growth-leaning cluster.
- The recommended action for service-gap agents assumes stockouts cause the shortfall, which was planted in the data and must be tested on real data.

### B.5 F5: Churn Early Warning (B7)

| Aspect | Detail |
| --- | --- |
| **Question it answers** | Which active agents will go quiet within 4 weeks, and why? |
| **Users** | Area manager and analyst |
| **Reads** | `agent_weekly`; the saved churn model and its held-out metrics |
| **Writes** | Nothing at request time |
| **Endpoints** | GET /intel/churn/risk, /intel/churn/agents/{code}, /intel/churn/metrics |
| **Screens** | /insights (churn tab), the dashboard retention panel, the copilot's retention section |
| **Evidence** | AUC 0.94 against 0.825 for a sharpest-drop rule; 16 of 16 test churners warned a median 3 weeks early (range 2 to 6); 0.2% false alarms |

**How it works**

1. A week is inactive below 25% of the agent's own normal, and churn is the first inactive week followed by another. The label for an active week is whether churn falls inside the next 4 weeks.
2. Features compare the agent with its own baseline and with similar agents in the same week, over several windows, plus stockout hours, ticket size and activity days.
3. Training weeks end 5 weeks before the 12-week test starts, so no training label looks into the test period.
4. A LightGBM binary classifier (200 trees, 15 leaves) scores each active agent. Agents already inactive are listed separately and are not scored.
5. The top three SHAP drivers become plain sentences in English and Bangla. A rule then picks a suggested action; for example an agent with 8 or more stockout hours in 4 weeks is told to fix service first.

**Rules and equations.** See A.5. MEDIUM at p ≥ 0.2 and HIGH at p ≥ 0.5. On 20 May the result was 2 HIGH (AG0235 and AG0206), 256 LOW and 42 already inactive.

**Outputs.** Probability, level, status, a 4-week horizon, up to three drivers with their SHAP values and text, the recommended action, four-week stockout hours, and activity against normal.

**Safeguards and limits**

- Peer adjustment keeps a holiday week from reading as churn.
- Probabilities cluster near 0 or 1 because the planted declines are clean; real churn will be gradual and noisier.
- The suggested action asserts that running out of money drives the drop. That link was planted in the data and must be tested before it is trusted.

### B.6 F6: Coverage Map (C1)

| Aspect | Detail |
| --- | --- |
| **Question it answers** | Where does the network lack agents, where are agents stretched, and where do existing agents run out of money? |
| **Users** | Area manager, analyst and leadership |
| **Reads** | `agents` (positions), `daily` volumes (28 days), unserved amounts in `hourly`, and `bd_towns.py` (2022 census population of 38 towns) |
| **Writes** | Nothing; the model is cached per date |
| **Endpoints** | GET /coverage/map, /coverage/gaps, /coverage/summary, /coverage/cells/{h3} |
| **Screens** | /coverage (a MapLibre hexagon map plus the ranked gap list), the dashboard coverage panel, the copilot's coverage section |
| **Evidence** | 304 hexagons on 20 May: 71 no coverage, 50 under-served, 8 capacity gaps, 108 low demand, 58 balanced, 9 over-supplied; untapped volume ৳5.9B a month |

**How it works**

1. Hexagons of about 250 km² are laid around every town and every agent.
2. Each hexagon's demand index is the sum of bell curves from the 38 towns. A town's weight is 3 × (population ÷ Dhaka's population) ^ 0.5, and its reach is 10 to 20 km.
3. The index is converted to money by a scale taken from the 70 hexagons that already hold agents.
4. Each agent's 28-day volume is spread: half to its own hexagon and half over the six neighbours.
5. Six ordered rules set each hexagon's type, and a recommendation says how many typical agents the shortfall would fill, capped at 8.
6. The GeoJSON for the map, the ranked gaps and the summary are all built from the same cached model.

**Rules and equations.** See A.7. The coverage ratio is supply divided by demand, and the first matching rule wins.

**Outputs.** Per hexagon: type, nearest town, demand, supply, coverage ratio, untapped and unserved amounts, agents inside and nearby, agents needed, and a recommendation sentence. The summary adds the demand covered (47.6%) and the volume lost to stockouts (৳249M a month).

**Safeguards and limits**

- The page tells the reader to treat the map as a ranking, not a measurement, and states where demand comes from.
- The 10 towns under the census's 100,000 line use a 50,000 placeholder, flagged in the file.
- The money totals swing between ৳3.1B and ৳22.0B as the assumed reach changes, while 3 or 4 of the 5 top gap towns survive each change.
- Agents sit in only 70 of 304 hexagons because the generator places them around 13 district centres, so "no coverage" partly reflects the synthetic network.

### B.7 F7: Copilot (C5)

| Aspect | Detail |
| --- | --- |
| **Question it answers** | What should I do this morning, and can I ask the system a question in plain words? |
| **Users** | Area manager and analyst |
| **Reads** | The outputs of F1 to F6 through service calls, never raw tables |
| **Writes** | Nothing. It cannot change data or contact anyone |
| **Endpoints** | GET /copilot/brief, POST /copilot/ask (a short question; the screen limits it to 300 characters) |
| **Screens** | /copilot: a brief with ranked priorities and section cards, and a question box with suggestion chips |
| **Evidence** | Covered by the backend smoke tests and a browser run in template mode. Gemini has not been tested live |

**How it works: the brief**

1. Five sections are gathered: liquidity, anomalies, retention, performance and coverage. Each returns a headline and items with drill-down links to the exact screen. A section that fails becomes a warning, not an error.
2. A template writes the headline, a summary in English and Bangla, and a ranked list of priorities.
3. If a key is present, LangChain with Gemini (`gemini-flash-latest`) rewrites the headline and summary and orders the priorities.
4. Every priority must match an item that was verified in step 1. Any that do not are dropped and counted in `dropped_unverified_priorities`, so the model cannot introduce an agent or a number that the tools did not return.
5. `generated_by` records whether the template or the model wrote the text, and the page styles the brief as AI-written only in the second case.

**How it works: ask**

1. With a model, a tool loop can call six read-only tools: `get_risk_summary`, `get_agent_overview`, `get_churn_risk`, `get_performance_segment`, `get_coverage_gaps` and `get_pending_alerts`.
2. Without a model, a keyword router picks the same tools and a template phrases the answer.
3. The response carries the answer, the tools that were used and who wrote it.

**Rules and equations.** None. This is a language layer over verified numbers, with no model of its own.

**Safeguards and limits**

- Read-only tools and verified priorities keep a fluent answer from becoming a wrong decision.
- Template mode is accurate but generic, for example "Open the details and decide this morning".
- Live Gemini behaviour, including Bangla quality and tool-call reliability, is the main untested area.

### B.8 F8: Access and role-aware dashboard

| Aspect | Detail |
| --- | --- |
| **Question it answers** | Who is this person, what may they see, and what do they need first? |
| **Users** | Everyone |
| **Reads and writes** | `users` (password hash, role, district, failed attempts, lock time, last login) and `refresh_tokens` |
| **Endpoints** | POST /auth/login, /auth/token, /auth/refresh, /auth/logout, /auth/change-password; GET /auth/me; GET /dashboard |
| **Screens** | /login, /dashboard, and the shell around every page: sidebar by role, demo-date picker, English and Bangla switch, account menu |
| **Evidence** | 25 page loads across three roles with no errors; cookies confirmed unreadable by page scripts; renewal, a corrupted token and sign-out all tested |

**How it works**

1. The sign-in form is a Server Action. It calls the API's login, and the web app stores an access token (60 minutes by default) and a refresh token (7 days) in httpOnly cookies.
2. `proxy.ts` runs before every page. With a valid access token it continues. With only a refresh token it renews quietly. If renewal fails it clears the cookies and sends the user to /login. A 401 from the API sends the user to /login once, with the cookies cleared, so there is no redirect loop.
3. Each refresh token works once, and reusing one ends every session of that user. Five wrong passwords lock the account for 15 minutes. The user is reloaded from the database on every request, so a disabled account is blocked immediately.
4. `GET /dashboard` returns a different set of panels per role, and one failing panel is shown as unavailable without breaking the page.

**Role views**

| Role | Panels |
| --- | --- |
| Area manager | Liquidity overview, riskiest agents, delivery route, pending alerts, retention, performance, coverage gaps |
| Agent | My status, next 24 hours, why this forecast, recent activity, my performance |
| Risk analyst | Pending alerts, review activity, model quality, performance, coverage gaps |

The demo accounts are `manager`, `dso_sylhet`, `agent_ag0142` and `analyst`, all with the password Pulse@2026.

**Safeguards and limits**

- Role limits are a screen rule. The menu, pages and panels follow the role, but the API does not yet refuse a logged-in user who calls another endpoint directly.
- Two requests renewing the same expired token at the same moment can log the user out, because refresh tokens are single-use. Links turn prefetching off to make this unlikely.
- The demo buttons are controlled by `NEXT_PUBLIC_SHOW_DEMO_LOGINS` and must be turned off before the site is shown outside the team.
