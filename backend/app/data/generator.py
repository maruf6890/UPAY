"""Synthetic ecosystem generator for upay Pulse (Track 05 - agent liquidity).

Everything here is SYNTHETIC. No real customer or agent data is used.
Outputs: PostgreSQL tables agents, hourly, daily, weather, anomaly_labels (+ data_store/DATA_ASSUMPTIONS.md)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.config import Settings, get_settings
from app.core.constants import ARCH_CODES, OPEN_HOURS, N_OPEN, REPORTING_THRESHOLD_BDT
from app.data.calendar_bd import build_calendar
from app.ml.simulation import simulate

# division, district, lat, lon, sampling weight, archetype mix
LOCATIONS = [
    ("Dhaka", "Dhaka", 23.81, 90.41, 0.22, {"urban_market": .5, "transit_hub": .2, "garment_zone": .3}),
    ("Dhaka", "Gazipur", 24.00, 90.42, 0.10, {"garment_zone": .7, "urban_market": .2, "transit_hub": .1}),
    ("Dhaka", "Narayanganj", 23.62, 90.50, 0.08, {"garment_zone": .6, "urban_market": .3, "transit_hub": .1}),
    ("Dhaka", "Tangail", 24.25, 89.92, 0.05, {"rural_remittance": .6, "urban_market": .2, "transit_hub": .2}),
    ("Chattogram", "Chattogram", 22.36, 91.78, 0.12, {"urban_market": .5, "transit_hub": .3, "garment_zone": .2}),
    ("Chattogram", "Cumilla", 23.46, 91.18, 0.06, {"rural_remittance": .6, "urban_market": .2, "transit_hub": .2}),
    ("Rajshahi", "Bogura", 24.85, 89.37, 0.07, {"rural_remittance": .65, "urban_market": .2, "transit_hub": .15}),
    ("Khulna", "Jashore", 23.17, 89.21, 0.05, {"rural_remittance": .6, "urban_market": .25, "transit_hub": .15}),
    ("Sylhet", "Sylhet", 24.90, 91.87, 0.07, {"rural_remittance": .55, "urban_market": .3, "transit_hub": .15}),
    ("Sylhet", "Sunamganj", 25.07, 91.40, 0.04, {"rural_remittance": .8, "transit_hub": .2}),
    ("Rangpur", "Rangpur", 25.75, 89.25, 0.06, {"rural_remittance": .55, "urban_market": .3, "transit_hub": .15}),
    ("Mymensingh", "Mymensingh", 24.75, 90.41, 0.05, {"rural_remittance": .5, "urban_market": .3, "transit_hub": .2}),
    ("Barishal", "Barishal", 22.70, 90.37, 0.03, {"rural_remittance": .6, "urban_market": .25, "transit_hub": .15}),
]

# Behaviour per agent archetype. dow order: Mon..Sun (Fri/Sat = weekend in Bangladesh)
ARCH = {
    "urban_market": dict(area="urban", base=(9, 18), size=(3500, 7000), out_share=(.45, .55),
                         dow=[1.05, 1.0, 1.0, 1.0, .75, .9, 1.1], salary=1.35, payday=1.0, remit=1.05,
                         eid_out=1.0, eid_in=.3, eid_hol=.45, rain=.15,
                         peaks=((11.5, 1.8, 1.0), (17.5, 1.8, 1.2))),
    "garment_zone": dict(area="urban", base=(10, 22), size=(2500, 4500), out_share=(.62, .74),
                         dow=[1.1, 1.05, 1.0, 1.0, .5, .8, 1.15], salary=1.45, payday=1.5, remit=1.1,
                         eid_out=1.8, eid_in=.2, eid_hol=.2, rain=.2,
                         peaks=((8.0, 1.2, .6), (19.5, 1.8, 1.5))),
    "rural_remittance": dict(area="rural", base=(3, 8), size=(4500, 9000), out_share=(.72, .84),
                             dow=[.95, .95, .95, .95, .9, .95, .95], salary=1.0, payday=1.0, remit=1.55,
                             eid_out=1.7, eid_in=.2, eid_hol=.35, rain=.35,
                             peaks=((10.5, 2.5, 1.0),)),
    "transit_hub": dict(area="semi_urban", base=(6, 14), size=(3000, 6000), out_share=(.50, .60),
                        dow=[1.0, 1.0, 1.0, 1.0, 1.2, 1.0, 1.0], salary=1.1, payday=1.0, remit=1.1,
                        eid_out=1.2, eid_in=.3, eid_hol=.7, rain=.2,
                        peaks=((8.0, 1.5, 1.0), (17.0, 2.2, 1.0))),
}
RAMADAN_PEAKS = ((16.0, 1.5, 1.0), (20.5, 1.2, 1.0))
FLOOD_EVENTS = [("Sylhet", "2025-06-20", "2025-06-24", 180.0), ("Sylhet", "2026-06-12", "2026-06-16", 190.0)]
ANOMALY_TYPES = ["structuring", "velocity_spike", "fake_cash_in", "odd_hours"]


def _profile(peaks) -> np.ndarray:
    h = np.array(OPEN_HOURS, dtype=float)
    p = np.full(N_OPEN, 0.15)
    for c, w, a in peaks:
        p += a * np.exp(-0.5 * ((h - c) / w) ** 2)
    return p / p.mean()


def make_weather(dates: pd.DatetimeIndex, rng) -> pd.DataFrame:
    rows = []
    month = dates.month.values
    p_rain = np.where((month >= 6) & (month <= 9), .55, np.where((month == 5) | (month == 10), .25, .06))
    for div in sorted({l[0] for l in LOCATIONS}):
        wet = rng.random(len(dates)) < p_rain
        rain = np.where(wet, rng.gamma(1.6, 18.0, len(dates)), 0.0)
        for ev_div, a, b, mm in FLOOD_EVENTS:
            if ev_div == div:
                m = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b))
                rain[m] = mm
        rows.append(pd.DataFrame({"date": dates, "division": div, "rain_mm": rain.astype("float32")}))
    w = pd.concat(rows, ignore_index=True)
    w["rain_3d"] = w.groupby("division")["rain_mm"].transform(lambda s: s.rolling(3, min_periods=1).sum()).astype("float32")
    return w


def make_agents(n: int, rng) -> pd.DataFrame:
    w = np.array([l[4] for l in LOCATIONS], dtype=float)
    w /= w.sum()
    idx = rng.choice(len(LOCATIONS), size=n, p=w)
    rows = []
    for i, li in enumerate(idx, start=1):
        div, dist, lat, lon, _, mix = LOCATIONS[li]
        names, probs = list(mix.keys()), np.array(list(mix.values()), dtype=float)
        arch = str(rng.choice(names, p=probs / probs.sum()))
        c = ARCH[arch]
        haat = sorted(rng.choice(7, size=2, replace=False).tolist()) if arch == "rural_remittance" else [-1, -1]
        rows.append(dict(
            agent_id=i, division=div, district=dist, archetype=arch, area_type=c["area"],
            lat=lat + rng.normal(0, .08), lon=lon + rng.normal(0, .08),
            base_rate=rng.uniform(*c["base"]), avg_txn_size=rng.uniform(*c["size"]),
            out_share=rng.uniform(*c["out_share"]), haat_day1=haat[0], haat_day2=haat[1],
            growth=rng.uniform(0.0, 0.25),
        ))
    ag = pd.DataFrame(rows)
    # Habitual morning targets (what the agent "usually" keeps) - sized from average daily flows
    e_out = ag.base_rate * ag.out_share * N_OPEN * ag.avg_txn_size
    e_in = ag.base_rate * (1 - ag.out_share) * N_OPEN * ag.avg_txn_size
    e_net = e_out - e_in
    ag["cash_target"] = ((np.maximum(e_net, 0) * 1.15 + 0.35 * e_out) * rng.uniform(.8, 1.3, n)).round(-2)
    ag["float_target"] = ((np.maximum(-e_net, 0) * 1.15 + 0.35 * e_in) * rng.uniform(.8, 1.4, n)).round(-2)
    ag["agent_code"] = ag.agent_id.map(lambda x: f"AG{x:04d}")
    return ag


def _day_multipliers(cfg, cal: pd.DataFrame):
    """Per-date (D,) multipliers for cash-out and cash-in flows of one archetype."""
    dom = cal.dom.values
    out = np.array(cfg["dow"])[cal.dow.values].astype(float)
    inn = out.copy()
    out *= np.where(dom <= 7, cfg["salary"], 1.0)
    out *= np.where((dom >= 7) & (dom <= 10), cfg["payday"], 1.0)
    out *= np.where((dom >= 8) & (dom <= 12), cfg["remit"], 1.0)
    d2e = cal.days_to_eid.values
    bump = np.where((d2e >= 1) & (d2e <= 10), np.exp(-0.5 * ((d2e - 4) / 2.5) ** 2), 0.0)  # pre-Eid crunch
    out *= 1 + cfg["eid_out"] * bump
    inn *= 1 + cfg["eid_in"] * bump
    hol = cal.is_eid_holiday.values == 1
    out = np.where(hol, out * cfg["eid_hol"], out)
    inn = np.where(hol, inn * cfg["eid_hol"], inn)
    ram = cal.is_ramadan.values == 1
    return out * np.where(ram, .92, 1.0), inn * np.where(ram, .92, 1.0)


def generate(settings: Settings | None = None, verbose: bool = True) -> dict:
    s = settings or get_settings()
    rng = np.random.default_rng(s.seed)
    dates = pd.date_range(s.start_date, s.end_date, freq="D")
    D, H = len(dates), N_OPEN
    wx_dates = pd.date_range(dates[0], dates[-1] + pd.Timedelta(days=5), freq="D")
    cal = build_calendar(dates)
    weather = make_weather(wx_dates, rng)
    agents = make_agents(s.n_agents, rng)
    A = len(agents)
    log = print if verbose else (lambda *a, **k: None)
    log(f"Generating {A} agents x {D} days x {H} open hours = {A*D*H:,} hourly rows")

    # ---------- expected multipliers (A, D) ----------
    m_out, m_in = np.ones((A, D)), np.ones((A, D))
    arch = agents.archetype.values
    for name, cfg in ARCH.items():
        sel = arch == name
        o, i = _day_multipliers(cfg, cal)
        m_out[sel], m_in[sel] = o[None, :], i[None, :]
    # market (haat) days for rural agents
    dow = cal.dow.values[None, :]
    haat = (dow == agents.haat_day1.values[:, None]) | (dow == agents.haat_day2.values[:, None])
    m_out *= np.where(haat, 1.5, 1.0)
    m_in *= np.where(haat, 1.2, 1.0)
    # weather
    wx = {div: g.set_index("date")["rain_mm"] for div, g in weather.groupby("division")}
    rain = np.stack([wx[d].reindex(dates).values for d in agents.division]).astype(float)
    sens = agents.archetype.map(lambda a: ARCH[a]["rain"]).values[:, None]
    rain_eff = 1 - sens * np.minimum(rain / 80.0, 1.0)
    # slow growth + HIDDEN daily agent shock (never given to the model as a feature)
    growth = 1 + agents.growth.values[:, None] * (np.arange(D)[None, :] / 365.0)
    latent = np.exp(rng.normal(0, .12, size=(A, D)))
    # ---------- anomaly episodes ----------
    n_anom = max(6, int(.07 * A))
    anom_agents = rng.choice(A, size=n_anom, replace=False)
    test_start = D - s.test_days
    episodes = []
    for k, a in enumerate(anom_agents):
        in_test = k < int(.6 * n_anom)
        lo, hi = (test_start, D - 6) if in_test else (30, max(31, test_start - 15))
        d0 = int(rng.integers(lo, hi))
        d1 = min(D - 1, d0 + int(rng.integers(4, 11)))
        episodes.append(dict(a=int(a), d0=d0, d1=d1, type=ANOMALY_TYPES[k % 4], strength=float(rng.choice([.55, 1.0]))))
    vel = np.ones((A, D))
    for e in episodes:
        sl = slice(e["d0"], e["d1"] + 1)
        if e["type"] == "velocity_spike":
            vel[e["a"], sl] = 1 + 2.5 * e["strength"]
    in_boost = np.ones((A, D))
    for e in episodes:
        if e["type"] == "fake_cash_in":
            in_boost[e["a"], slice(e["d0"], e["d1"] + 1)] = 1 + 1.0 * e["strength"]

    # ---------- hourly demand (A, D, H) ----------
    prof_n = np.stack([_profile(ARCH[a]["peaks"]) for a in ARCH])
    prof_r = np.stack([_profile(RAMADAN_PEAKS)] * len(ARCH))
    code = agents.archetype.map({k: i for i, k in enumerate(ARCH)}).values
    ram = (cal.is_ramadan.values == 1)[None, :, None]
    prof = np.where(ram, prof_r[code][:, None, :], prof_n[code][:, None, :])        # (A, D, H)
    base = agents.base_rate.values[:, None, None]
    osh = agents.out_share.values[:, None, None]
    common = (growth * rain_eff * latent * vel)[:, :, None] * prof
    lam_out = base * osh * common * m_out[:, :, None]
    lam_in = base * (1 - osh) * common * (m_in * in_boost)[:, :, None]
    cnt_out = rng.poisson(lam_out).astype(np.float32)
    cnt_in = rng.poisson(lam_in).astype(np.float32)
    size = agents.avg_txn_size.values[:, None, None]
    d2e = cal.days_to_eid.values
    size_up = (1 + .25 * np.where((d2e >= 1) & (d2e <= 10), np.exp(-0.5 * ((d2e - 4) / 2.5) ** 2), 0.0))[None, :, None]
    k_shape = 2.0   # sum of n gamma(k, size/k) txns = gamma(n*k, size/k)
    amt_out = np.where(cnt_out > 0, rng.gamma(np.maximum(cnt_out * k_shape, 1e-6), size * size_up / k_shape), 0.0).astype(np.float32)
    amt_in = np.where(cnt_in > 0, rng.gamma(np.maximum(cnt_in * k_shape, 1e-6), size / k_shape), 0.0).astype(np.float32)

    # ---------- balances under the agent's habitual restocking behaviour ----------
    log("Simulating agent cash / e-float balances ...")
    t_cash = np.repeat(agents.cash_target.values[:, None], D, axis=1)
    t_flt = np.repeat(agents.float_target.values[:, None], D, axis=1)
    active = (rng.random((A, D)) > .15).astype(float)        # agents skip their morning restock 15% of days
    sim = simulate(amt_out, amt_in, t_cash, t_flt, agents.cash_target.values, agents.float_target.values,
                   active=active, emergency_prob=.30, rng=rng)

    # ---------- long hourly table ----------
    ts = (dates.values[:, None].astype("datetime64[ns]") + np.array(OPEN_HOURS, dtype="timedelta64[h]")[None, :]).ravel()
    hourly = pd.DataFrame({
        "agent_id": np.repeat(agents.agent_id.values.astype("int32"), D * H),
        "timestamp": np.tile(ts, A),
        "cash_out_cnt": cnt_out.ravel(), "cash_in_cnt": cnt_in.ravel(),
        "cash_out_amt": amt_out.ravel(), "cash_in_amt": amt_in.ravel(),
        "cash_balance": sim["cash_end"].ravel(), "float_balance": sim["flt_end"].ravel(),
        "stockout": sim["stockout"].ravel(), "unserved_amt": sim["unserved"].ravel(),
    })

    # ---------- daily signals for anomaly detection ----------
    tot_cnt = (cnt_out + cnt_in).sum(2)
    tot_out, tot_in = amt_out.sum(2), amt_in.sum(2)
    near = rng.beta(1.2, 60, (A, D))
    repeat = rng.beta(2.0, 10.0, (A, D))
    night = rng.poisson(.6, (A, D)).astype(float)
    rnd = rng.beta(4, 12, (A, D))
    is_anom = np.zeros((A, D), dtype=bool)
    a_type = np.full((A, D), "", dtype=object)
    for e in episodes:
        a, sl, st = e["a"], slice(e["d0"], e["d1"] + 1), e["strength"]
        n = e["d1"] - e["d0"] + 1
        is_anom[a, sl] = True
        a_type[a, sl] = e["type"]
        if e["type"] == "structuring":
            near[a, sl] = (1 - st) * near[a, sl] + st * rng.beta(7, 13, n)
            rnd[a, sl] = (1 - st) * rnd[a, sl] + st * rng.beta(9, 7, n)
        elif e["type"] == "fake_cash_in":
            repeat[a, sl] = (1 - st) * repeat[a, sl] + st * rng.beta(9, 6, n)
            rnd[a, sl] = (1 - st) * rnd[a, sl] + st * rng.beta(9, 7, n)
        elif e["type"] == "odd_hours":
            night[a, sl] = (1 - st) * night[a, sl] + st * rng.poisson(14, n)
        elif e["type"] == "velocity_spike":
            night[a, sl] += rng.poisson(2 * st, n)
    peak_share = (cnt_out + cnt_in).max(2) / np.maximum(tot_cnt, 1)
    daily = pd.DataFrame({
        "agent_id": np.repeat(agents.agent_id.values.astype("int32"), D),
        "date": np.tile(dates.values, A),
        "txn_count": tot_cnt.ravel(),
        "out_amt": tot_out.ravel(), "in_amt": tot_in.ravel(),
        "avg_txn_size": ((tot_out + tot_in) / np.maximum(tot_cnt, 1)).ravel(),
        "out_in_ratio": (tot_out / (tot_in + 1.0)).ravel(),
        "peak_hour_share": peak_share.ravel(),
        "near_threshold_share": near.ravel(), "repeat_counterparty_share": repeat.ravel(),
        "night_txn_cnt": night.ravel(), "round_amount_share": rnd.ravel(),
        "is_anomaly": is_anom.ravel(), "anomaly_type": a_type.ravel().astype(str),   # labels: evaluation only
    })
    labels = pd.DataFrame([{"agent_id": int(agents.agent_id.values[e["a"]]), "start": dates[e["d0"]], "end": dates[e["d1"]],
                            "type": e["type"], "strength": e["strength"]} for e in episodes])

    # ---------- save to PostgreSQL (migrate first, then COPY) ----------
    import asyncio
    from app.db import migrate
    from app.db.pool import run_with_conn
    from app.db.queries import save_tables
    log("Applying database migrations ...")
    asyncio.run(migrate.up(log=log))
    log("Loading into PostgreSQL (COPY) ...")
    run_with_conn(lambda db: save_tables(db, dict(agents=agents, hourly=hourly, daily=daily, weather=weather, labels=labels), log))
    s.data_dir.mkdir(parents=True, exist_ok=True)
    (s.data_dir / "DATA_ASSUMPTIONS.md").write_text(ASSUMPTIONS, encoding="utf-8")
    log(f"Done | stockout agent-hours: {hourly.stockout.mean():.2%} of open hours")
    return dict(agents=agents, hourly=hourly, daily=daily, weather=weather, labels=labels)


ASSUMPTIONS = f"""# Synthetic data assumptions (upay Pulse)

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
* **Reporting threshold** - illustrative BDT {REPORTING_THRESHOLD_BDT:,} (assumption).
* **Commission** - 0.5% revenue on transaction value (assumption) used only to convert unserved volume into BDT impact.
* **Weather forecast** - the model receives actual rainfall as if it were a perfect forecast (assumption).
* **Split** - time-based: train < validation (calibration) < test (last 60 days, contains Eid-ul-Adha 2026, unseen in training).
"""
