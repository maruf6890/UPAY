"""python3 -m scripts.verify_anomaly

A one-minute PASS/FAIL check that the anomaly-detector fix is in place and really working.
It needs the database and artifacts/ (not the API server). Exit code 0 = everything passed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd

from app.core.config import get_settings
from app.data.loader import load_tables
from app.ml import anomaly as anom


def run(artifact_dir: Path | None = None) -> bool:
    s = get_settings()
    artifact_dir = Path(artifact_dir or s.artifact_dir)
    ok = True

    def check(passed: bool, text: str, warn_only: bool = False):
        nonlocal ok
        if not passed and not warn_only:
            ok = False
        print(f"  [{'PASS' if passed else ('WARN' if warn_only else 'FAIL')}] {text}")

    print("1) Is the fix in the code, and was the model retrained with it?")
    check(anom.MIN_LOG_SPREAD >= 0.3, f"app/ml/anomaly.py: MIN_LOG_SPREAD = {anom.MIN_LOG_SPREAD} (needs 0.3)")
    saved = json.loads((artifact_dir / "metrics.json").read_text()).get("anomaly", {})
    check(saved.get("min_log_spread") == anom.MIN_LOG_SPREAD,
          f"artifacts/metrics.json was written by the fixed code (saved value: {saved.get('min_log_spread')}). If not: python3 -m scripts.train_anomaly")

    print("\n2) Re-score the real data with the saved model and look at every planted episode in the test window")
    t = load_tables(s)
    agents, daily = t["agents"].sort_values("agent_id").reset_index(drop=True), t["daily"]
    end = pd.Timestamp(daily.date.max())
    test_start = end - pd.Timedelta(days=s.test_days - 1)
    bundle = joblib.load(artifact_dir / "anomaly_model.joblib")
    thr = bundle["thresholds"]["medium"]
    scored = anom.score(bundle["model"], anom.build_features(daily, agents))
    labels = t["labels"].assign(start=lambda x: pd.to_datetime(x["start"]), end=lambda x: pd.to_datetime(x["end"]))

    caught: dict[str, list[bool]] = {}
    cause_named = []                                   # for odd-hours: is "off-hours" among the top 3 reasons on the peak day?
    for _, e in labels.iterrows():
        m = (scored.agent_id == e.agent_id) & (scored.date >= e.start) & (scored.date <= e.end) & (scored.date >= test_start)
        if not m.any():
            continue
        window = scored[m]
        peak = window.loc[window.alert_score.idxmax()]
        hit = bool(peak.alert_score >= thr)
        caught.setdefault(str(e["type"]), []).append(hit)
        if e["type"] == "odd_hours":
            names = [r["signal"] for r in anom.reasons(peak, top=3)]
            cause_named.append("night_txn_cnt" in names)
            code = agents.set_index("agent_id").loc[e.agent_id, "agent_code"]
            print(f"     odd-hours {code}: peak score {peak.alert_score:.3f} vs alert line {thr:.3f} -> {'ALERT' if hit else 'MISSED'}; top reasons: {names}")
    for k, v in sorted(caught.items()):
        print(f"     {k:<15} caught {sum(v)}/{len(v)}")
    total_hits, total = sum(sum(v) for v in caught.values()), sum(len(v) for v in caught.values())
    odd = caught.get("odd_hours", [])
    check(bool(odd) and all(odd), f"every odd-hours episode raises an alert ({sum(odd)}/{len(odd)})  <- the thing that was broken")
    check(total_hits >= total - 1, f"at least all-but-one planted episode is caught overall ({total_hits}/{total})")
    check(sum(cause_named) >= max(1, len(cause_named) - 1), f"the alert names the right cause (off-hours) for {sum(cause_named)}/{len(cause_named)} odd-hours episodes")

    print("\n3) Is it still quiet enough for a human to review?")
    te = scored[scored.date >= test_start]
    flagged = te.alert_score >= thr
    false_per_day = float((flagged & ~te.is_anomaly).groupby(te.date).sum().mean())
    check(false_per_day <= 4.0, f"false alerts per day = {false_per_day:.1f} (the fixed model gave 2.8; above 4 means something is off)")

    print("\nRESULT:", "PASS - the fix is working" if ok else "FAIL - see the lines marked FAIL above")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)