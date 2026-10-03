"""End-to-end training + evaluation pipeline.  Run with:  python -m scripts.train"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from app.core.config import Settings, get_settings
from app.core.constants import N_OPEN
from app.data.loader import load_tables
from app.ml import anomaly as anom
from app.ml.features import build_feature_frame_chunked, compute_scale, to_cube
from app.ml.forecasting import baseline_quantiles, predict_quantiles, save_artifacts, train_quantile_models
from app.ml.liquidity import calibrate_k, cumulative_bands, peak_need
from app.ml.simulation import simulate


def _pinball(y, q, a):
    d = y - q
    return float(np.mean(np.maximum(a * d, (a - 1) * d)))


def run_training(s: Settings | None = None, log=lambda *a: print(*a, flush=True)) -> dict:
    s = s or get_settings()
    t = load_tables(s)
    agents, hourly, daily, weather = t["agents"].sort_values("agent_id").reset_index(drop=True), t["hourly"], t["daily"], t["weather"]
    end = hourly.timestamp.max().normalize()
    test_start = end - pd.Timedelta(days=s.test_days - 1)
    val_start = test_start - pd.Timedelta(days=s.val_days)
    train_end, val_end = val_start - pd.Timedelta(days=1), test_start - pd.Timedelta(days=1)
    log(f"Split  train<= {train_end.date()} | val {val_start.date()}..{val_end.date()} | test {test_start.date()}..{end.date()}")

    scale = compute_scale(hourly, upto=train_end)
    log("Building features ...")
    frame = build_feature_frame_chunked(hourly, agents, weather, scale)
    sub = frame[frame.date > train_end].reset_index(drop=True)
    models = train_quantile_models(frame, train_end, val_end, s, log)
    del frame
    import gc; gc.collect()
    log("Predicting validation + test ...")

    # ---------- predictions for validation + test ----------
    q = predict_quantiles(models, sub)
    b = baseline_quantiles(sub)
    A = sub.agent_id.nunique()
    is_val = (sub.date <= val_end).to_numpy()
    cube = lambda arr, m: arr[m].reshape(A, -1, N_OPEN)
    qv = [cube(q[c].to_numpy(), is_val) for c in ("q10", "q50", "q90")]
    bv = [cube(b[c].to_numpy(), is_val) for c in ("q10", "q50", "q90")]
    qt = [cube(q[c].to_numpy(), ~is_val) for c in ("q10", "q50", "q90")]
    bt = [cube(b[c].to_numpy(), ~is_val) for c in ("q10", "q50", "q90")]
    net_v, net_t = cube(sub.net.to_numpy(), is_val), cube(sub.net.to_numpy(), ~is_val)
    out_t, in_t = cube(sub.out.to_numpy(), ~is_val), cube(sub.inn.to_numpy(), ~is_val)

    # ---------- calibrate cumulative P90 bands on validation (both AI and baseline, so the comparison is fair) ----------
    calib = dict(
        k_cash=calibrate_k(*qv, net_v, "cash"), k_flt=calibrate_k(*qv, net_v, "float"),
        k_cash_base=calibrate_k(*bv, net_v, "cash"), k_flt_base=calibrate_k(*bv, net_v, "float"),
        train_end=str(train_end.date()), val_end=str(val_end.date()), test_start=str(test_start.date()),
        reserve_bdt=s.reserve_bdt,
    )
    log(f"Calibration factors: {calib}")

    # ---------- test metrics ----------
    y, sc = sub.net.to_numpy()[~is_val], sub.scale.to_numpy()[~is_val]
    ai50, ai90, ai10 = (q[c].to_numpy()[~is_val] for c in ("q50", "q90", "q10"))
    b50, b90 = b["q50"].to_numpy()[~is_val], b["q90"].to_numpy()[~is_val]
    day_gross = (out_t + in_t).sum(2)
    metrics = {"split": {k: calib[k] for k in ("train_end", "val_end", "test_start")}}
    metrics["hourly_forecast"] = dict(
        mae_norm_ai=float(np.mean(np.abs(y - ai50) / sc)), mae_norm_baseline=float(np.mean(np.abs(y - b50) / sc)),
        pinball_p90_ai=_pinball(y / sc, ai90 / sc, .9), pinball_p90_baseline=_pinball(y / sc, b90 / sc, .9),
        coverage_p90_ai=float(np.mean(y <= ai90)), coverage_p90_baseline=float(np.mean(y <= b90)),
        coverage_p10_ai=float(np.mean(y >= ai10)),
        daily_net_wape_ai=float(np.abs(net_t.sum(2) - qt[1].sum(2)).sum() / day_gross.sum()),
        daily_net_wape_baseline=float(np.abs(net_t.sum(2) - bt[1].sum(2)).sum() / day_gross.sum()),
    )
    h = metrics["hourly_forecast"]
    h["mae_improvement_pct"] = 100 * (1 - h["mae_norm_ai"] / h["mae_norm_baseline"])
    h["daily_wape_improvement_pct"] = 100 * (1 - h["daily_net_wape_ai"] / h["daily_net_wape_baseline"])

    ai_b = cumulative_bands(*qt, calib["k_cash"], calib["k_flt"])
    bs_b = cumulative_bands(*bt, calib["k_cash_base"], calib["k_flt_base"])
    need = dict(ai_cash=peak_need(ai_b["cash_p90"]), ai_flt=peak_need(ai_b["flt_p90"]),
                base_cash=peak_need(bs_b["cash_p90"]), base_flt=peak_need(bs_b["flt_p90"]))
    cum = np.cumsum(net_t, axis=2)
    act_cash, act_flt = np.maximum(cum.max(2), 0), np.maximum((-cum).max(2), 0)
    metrics["peak_drain_p90"] = dict(
        coverage_cash_ai=float((act_cash <= need["ai_cash"] + 1e-6).mean()), coverage_cash_baseline=float((act_cash <= need["base_cash"] + 1e-6).mean()),
        coverage_float_ai=float((act_flt <= need["ai_flt"] + 1e-6).mean()), coverage_float_baseline=float((act_flt <= need["base_flt"] + 1e-6).mean()),
        mean_buffer_bdt_ai=float((need["ai_cash"] + need["ai_flt"]).mean()),
        mean_buffer_bdt_baseline=float((need["base_cash"] + need["base_flt"]).mean()),
    )
    p = metrics["peak_drain_p90"]
    p["buffer_reduction_pct_at_equal_coverage"] = 100 * (1 - p["mean_buffer_bdt_ai"] / p["mean_buffer_bdt_baseline"])

    # ---------- policy simulation on the held-out test period ----------
    last_prev = val_end + pd.Timedelta(hours=22)
    bal = hourly[hourly.timestamp == last_prev].sort_values("agent_id")
    cash0, flt0 = bal.cash_balance.to_numpy(float), bal.float_balance.to_numpy(float)
    D = out_t.shape[1]
    res_ = s.reserve_bdt
    hab_t = (np.repeat(agents.cash_target.to_numpy()[:, None], D, 1), np.repeat(agents.float_target.to_numpy()[:, None], D, 1))
    ma_t = (need["base_cash"] + res_, need["base_flt"] + res_)
    ai_t = (need["ai_cash"] + res_, need["ai_flt"] + res_)
    o64, i64 = out_t.astype(float), in_t.astype(float)
    sims = {"AI (LightGBM P90)": simulate(o64, i64, *ai_t, cash0, flt0)}
    target_liq = float(sims["AI (LightGBM P90)"]["start_liq"].mean())

    def match(tc, tf):
        """Scale a policy's targets so its average start-of-day liquidity equals the AI policy's (fair comparison)."""
        lo, hi = 0.2, 6.0
        for _ in range(12):
            f = (lo + hi) / 2
            if simulate(o64, i64, tc * f, tf * f, cash0, flt0)["start_liq"].mean() < target_liq:
                lo = f
            else:
                hi = f
        return tc * f, tf * f

    sims["habitual (status quo)"] = simulate(o64, i64, *hab_t, cash0, flt0)
    sims["7-day moving average"] = simulate(o64, i64, *ma_t, cash0, flt0)
    sims["habitual (liquidity-matched)"] = simulate(o64, i64, *match(*hab_t), cash0, flt0)
    sims["7-day moving average (liquidity-matched)"] = simulate(o64, i64, *match(*ma_t), cash0, flt0)
    sim_out = {}
    for name, r in sims.items():
        sim_out[name] = dict(
            stockout_agent_hours=int(r["stockout"].sum()), stockout_hour_rate=float(r["stockout"].mean()),
            agent_days_with_stockout=int(r["stockout"].any(axis=2).sum()), unserved_bdt=float(r["unserved"].sum()),
            lost_commission_bdt=float(r["unserved"].sum() * s.commission_rate),
            liquidity_injected_bdt=float(r["injected"].sum()), avg_start_of_day_liquidity_bdt=float(r["start_liq"].mean()),
        )
    ai = sim_out["AI (LightGBM P90)"]
    hab_m, ma_m = sim_out["habitual (liquidity-matched)"], sim_out["7-day moving average (liquidity-matched)"]
    red = lambda base: 100 * (1 - ai["stockout_agent_hours"] / max(base["stockout_agent_hours"], 1))
    sim_out["summary"] = dict(
        note="Matched = same average start-of-day liquidity as the AI policy, so gains come from smarter allocation, not just holding more cash.",
        stockout_hours_reduction_vs_habitual_pct=red(sim_out["habitual (status quo)"]),
        stockout_hours_reduction_vs_habitual_matched_pct=red(hab_m),
        stockout_hours_reduction_vs_moving_avg_matched_pct=red(ma_m),
        unserved_volume_saved_vs_habitual_matched_bdt=hab_m["unserved_bdt"] - ai["unserved_bdt"],
        commission_saved_vs_habitual_matched_bdt=hab_m["lost_commission_bdt"] - ai["lost_commission_bdt"],
        n_agents=int(A), test_days=int(D),
    )
    metrics["policy_simulation"] = sim_out

    # ---------- fairness (urban/semi-urban/rural and by division) ----------
    ag = agents.set_index("agent_id").loc[np.sort(sub.agent_id.unique())]
    mae_ai_a = (np.abs(y - ai50) / sc).reshape(A, -1).mean(1)
    mae_b_a = (np.abs(y - b50) / sc).reshape(A, -1).mean(1)
    cov_a = (act_cash <= need["ai_cash"] + 1e-6).mean(1)
    so_h = sims["habitual (liquidity-matched)"]["stockout"].mean((1, 2))
    so_a = sims["AI (LightGBM P90)"]["stockout"].mean((1, 2))
    fair = pd.DataFrame({"area_type": ag.area_type.values, "division": ag.division.values, "mae_norm_ai": mae_ai_a,
                         "mae_norm_baseline": mae_b_a, "p90_cash_coverage_ai": cov_a,
                         "stockout_rate_habitual": so_h, "stockout_rate_ai": so_a})
    metrics["fairness"] = {g: fair.groupby(g).mean(numeric_only=True).round(4).reset_index().to_dict("records") for g in ("area_type", "division")}

    # ---------- anomaly detection ----------
    ad, thr = anom.fit(daily, agents, train_end, s)
    te = ad[ad.date >= test_start]
    auc = float(roc_auc_score(te.is_anomaly, te.alert_score))
    rprec = []
    for _, g in te.groupby("date"):
        k = int(g.is_anomaly.sum())
        if k:
            rprec.append(g.nlargest(k, "alert_score").is_anomaly.mean())
    flagged = te.alert_score >= thr["medium"]
    labels = t["labels"]
    ep_hit = []
    for _, e in labels.iterrows():
        m = (ad.agent_id == e.agent_id) & (ad.date >= e.start) & (ad.date <= e.end) & (ad.date >= test_start)
        if m.any():
            ep_hit.append(bool((ad.loc[m, "alert_score"] >= thr["medium"]).any()))
    metrics["anomaly"] = dict(
        roc_auc_agent_day=auc, r_precision_mean=float(np.mean(rprec)) if rprec else None,
        precision_at_threshold=float(te.loc[flagged, "is_anomaly"].mean()) if flagged.any() else None,
        recall_at_threshold=float(flagged[te.is_anomaly].mean()), episode_detection_rate=float(np.mean(ep_hit)) if ep_hit else None,
        false_alerts_per_day=float((flagged & ~te.is_anomaly).groupby(te.date).sum().mean()), thresholds=thr,
    )

    calib["thresholds_anomaly"] = thr
    save_artifacts(models, scale, calib, s)
    (s.artifact_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, default=float))
    from app.db.pool import run_with_conn
    from app.db.queries import insert_model_run
    run_id = run_with_conn(lambda db: insert_model_run(db, metrics, calib))
    log(f"Saved model run #{run_id} to PostgreSQL (model_runs)")
    log(json.dumps({k: metrics[k] for k in ("hourly_forecast", "peak_drain_p90")}, indent=2, default=float))
    log(json.dumps(metrics["policy_simulation"], indent=2, default=float))
    log(json.dumps(metrics["anomaly"], indent=2, default=float))
    return metrics
