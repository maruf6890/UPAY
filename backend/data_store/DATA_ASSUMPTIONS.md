# Synthetic data assumptions (upay Pulse)

All data is synthetic. No production upay data or real PII is used.

* **Agents** - archetypes: urban_market, garment_zone, rural_remittance, transit_hub across 13 districts / 8 divisions.
* **Hours** - agents trade 07:00-22:59 (16 rows per agent-day). Timestamp = start of the hour.
* **Demand** - Poisson transaction counts x Gamma-distributed amounts. Recorded demand is *attempted* demand,
  so stockouts do not censor the training target.
* **Calendar effects** - Ramadan (evening shift), pre-Eid cash-out crunch (peaks ~4 days before Eid), Eid holidays,
  salary week (days 1-7), garment payday (7-10), remittance window (8-12), rural haat (market) days, Friday/Saturday weekend.
  Eid / Ramadan dates are approximate.
* **Weather** - monsoon rainfall by division + two synthetic flood events in Sylhet; rain reduces footfall.
* **Hidden factors** - a daily lognormal agent-level shock (sigma=0.12) and slow growth are NOT visible to the model.
* **Balances** - two balances per agent (physical cash, e-float). Cash-out: cash down, float up. Cash-in: reverse.
  Habitual policy: morning top-up to a fixed target (skipped 15% of days), 30% chance of an emergency restock after a stockout.
* **Stockout** - an hour with more than BDT 2,000 of unserved demand (about one failed typical transaction) because cash (for cash-outs) or float (for cash-ins) ran out.
* **Anomalies** - ~7% of agents get one 4-10 day episode: structuring (near-threshold amounts), velocity spike,
  fake cash-in (repeat counterparties), odd hours. Half have weak strength. Labels are used ONLY for evaluation.
* **Reporting threshold** - illustrative BDT 50,000 (assumption).
* **Commission** - 0.5% revenue on transaction value (assumption) used only to convert unserved volume into BDT impact.
* **Weather forecast** - the model receives actual rainfall as if it were a perfect forecast (assumption).
* **Split** - time-based: train < validation (calibration) < test (last 60 days, contains Eid-ul-Adha 2026, unseen in training).
