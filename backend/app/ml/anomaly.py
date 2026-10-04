"""Agent anomaly detection: Isolation Forest on own-history z-scores + peer z-scores (same archetype, same day)."""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.core.config import Settings
from app.core.constants import REPORTING_THRESHOLD_BDT

SIGNALS = ["txn_count", "avg_txn_size", "out_in_ratio", "peak_hour_share", "near_threshold_share",
           "repeat_counterparty_share", "night_txn_cnt", "round_amount_share"]
LOG_SIGNALS = {"txn_count", "avg_txn_size", "out_in_ratio", "night_txn_cnt"}
FEATS = [f"{s}__{k}" for s in SIGNALS for k in ("own", "peer")]

# Off-hours transactions (and other "mostly zero" counts) have a spread of exactly 0 for many agents and peer groups.
# Without a floor, ONE stray night transaction reads as +8 standard deviations, so the signal looks "extreme" on a third of
# normal agent-days and the Isolation Forest stops treating it as rare (odd-hours episodes were missed: 0 of 3 in testing).
# A floor of 0.3 in log units (about a 35% change) keeps ordinary noise ordinary and real episodes extreme.
MIN_LOG_SPREAD = 0.3

REASON_TEXT = {
    "txn_count": ("Transaction volume", "{x:.0f}/day vs peer median {m:.0f}"),
    "avg_txn_size": ("Average ticket size", "৳{x:,.0f} vs peer median ৳{m:,.0f}"),
    "out_in_ratio": ("Cash-out / cash-in ratio", "{x:.2f} vs peer median {m:.2f}"),
    "peak_hour_share": ("Burstiness (share of day's txns in one hour)", "{x:.0%} vs peer median {m:.0%}"),
    "near_threshold_share": (f"Transactions just under the ৳{REPORTING_THRESHOLD_BDT:,} threshold (possible structuring)", "{x:.0%} vs peer median {m:.0%}"),
    "repeat_counterparty_share": ("Cash-ins from repeat counterparties", "{x:.0%} vs peer median {m:.0%}"),
    "night_txn_cnt": ("Off-hours transactions", "{x:.0f} vs peer median {m:.0f}"),
    "round_amount_share": ("Round-amount transactions", "{x:.0%} vs peer median {m:.0%}"),
}


def build_features(daily: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    d = daily.merge(agents[["agent_id", "archetype"]], on="agent_id").sort_values(["agent_id", "date"]).reset_index(drop=True)
    for s in SIGNALS:
        x = np.log1p(d[s]) if s in LOG_SIGNALS else d[s]
        floor = MIN_LOG_SPREAD if s in LOG_SIGNALS else 0.0
        d[f"_{s}"] = x
        g = d.groupby("agent_id")[f"_{s}"]
        mean = g.transform(lambda v: v.rolling(28, min_periods=7).mean().shift(1))
        std = g.transform(lambda v: v.rolling(28, min_periods=7).std().shift(1))
        own = ((x - mean) / np.maximum(np.maximum(std, floor), 1e-3 * np.abs(mean) + 1e-6)).clip(-8, 8)
        # remove the market-wide move (Eid, salary week, rain ...) so that only agent-specific change remains
        d[f"{s}__own"] = own - own.groupby(d["date"]).transform("median")
        key = [d["archetype"], d["date"]]
        med = x.groupby(key).transform("median")
        mad = (x - med).abs().groupby(key).transform("median")
        d[f"{s}__peer"] = ((x - med) / np.maximum(np.maximum(1.4826 * mad, floor), 1e-3 * np.abs(med) + 1e-6)).clip(-8, 8)
        d[f"{s}__pmed"] = d.groupby(key)[s].transform("median")      # raw peer median, for explanations
    d[FEATS] = d[FEATS].fillna(0.0)
    return d


def fit(daily: pd.DataFrame, agents: pd.DataFrame, train_end: pd.Timestamp, s: Settings):
    d = build_features(daily, agents)
    tr = d[d.date <= train_end]
    model = IsolationForest(n_estimators=300, max_samples=4096, contamination="auto", random_state=s.seed, n_jobs=-1)
    model.fit(tr[FEATS])
    d = score(model, d)
    thr = {"medium": float(d.loc[d.date <= train_end, "alert_score"].quantile(.99)),
           "high": float(d.loc[d.date <= train_end, "alert_score"].quantile(.998))}
    joblib.dump({"model": model, "thresholds": thr}, s.artifact_dir / "anomaly_model.joblib")
    return d, thr


def score(model, d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["day_score"] = -model.score_samples(d[FEATS])
    d["alert_score"] = d.groupby("agent_id")["day_score"].transform(lambda v: v.rolling(2, min_periods=1).mean())
    return d


def load(s: Settings):
    b = joblib.load(s.artifact_dir / "anomaly_model.joblib")
    return b["model"], b["thresholds"]


def reasons(row: pd.Series, top: int = 3) -> list[dict]:
    strength = {sg: max(abs(row[f"{sg}__own"]), abs(row[f"{sg}__peer"])) for sg in SIGNALS}
    out = []
    for sg in sorted(strength, key=strength.get, reverse=True)[:top]:
        label, tmpl = REASON_TEXT[sg]
        out.append({"signal": sg, "label": label, "detail": tmpl.format(x=row[sg], m=row[f"{sg}__pmed"]),
                    "z_peer": round(float(row[f"{sg}__peer"]), 1), "z_own": round(float(row[f"{sg}__own"]), 1)})
    return out


def evaluate(ad: pd.DataFrame, thr: dict, labels: pd.DataFrame, test_start: pd.Timestamp) -> dict:
    """Held-out quality of the detector. Used by the full training pipeline and by scripts/train_anomaly.py.

    The detector is unsupervised: the planted episodes in `labels` are only used here, to measure it."""
    from sklearn.metrics import roc_auc_score
    te = ad[ad.date >= test_start]
    rprec = []
    for _, g in te.groupby("date"):
        k = int(g.is_anomaly.sum())
        if k:
            rprec.append(g.nlargest(k, "alert_score").is_anomaly.mean())
    flagged = te.alert_score >= thr["medium"]
    labels = labels.assign(start=pd.to_datetime(labels["start"]), end=pd.to_datetime(labels["end"]))
    by_type: dict[str, list[bool]] = {}
    for _, e in labels.iterrows():
        m = (ad.agent_id == e.agent_id) & (ad.date >= e.start) & (ad.date <= e.end) & (ad.date >= test_start)
        if m.any():
            by_type.setdefault(str(e["type"]), []).append(bool((ad.loc[m, "alert_score"] >= thr["medium"]).any()))
    hits = [h for v in by_type.values() for h in v]
    return dict(
        roc_auc_agent_day=float(roc_auc_score(te.is_anomaly, te.alert_score)),
        r_precision_mean=float(np.mean(rprec)) if rprec else None,
        precision_at_threshold=float(te.loc[flagged, "is_anomaly"].mean()) if flagged.any() else None,
        recall_at_threshold=float(flagged[te.is_anomaly].mean()),
        episode_detection_rate=float(np.mean(hits)) if hits else None,
        episodes_caught=f"{sum(hits)}/{len(hits)}",
        episode_detection_by_type={k: f"{sum(v)}/{len(v)}" for k, v in sorted(by_type.items())},
        false_alerts_per_day=float((flagged & ~te.is_anomaly).groupby(te.date).sum().mean()),
        thresholds=thr, min_log_spread=MIN_LOG_SPREAD,
    )