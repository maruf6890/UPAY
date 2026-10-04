"""python3 -m scripts.train_anomaly

Retrains ONLY the anomaly detector (Isolation Forest) and refreshes its metrics, thresholds and model-run record.
Use it after changing app/ml/anomaly.py, instead of retraining the 2-million-row forecasting models.
Restart the API afterwards so it loads the new model.
"""
import json
import shutil

import pandas as pd

from app.core.config import get_settings
from app.data.loader import load_tables
from app.db.pool import run_with_conn
from app.db.queries import insert_model_run
from app.ml import anomaly as anom


def main():
    s = get_settings()
    t = load_tables(s)
    agents = t["agents"].sort_values("agent_id").reset_index(drop=True)
    daily = t["daily"]
    end = pd.Timestamp(daily.date.max())
    test_start = end - pd.Timedelta(days=s.test_days - 1)
    train_end = test_start - pd.Timedelta(days=s.val_days) - pd.Timedelta(days=1)
    print(f"Split  train<= {train_end.date()} | test {test_start.date()}..{end.date()}")

    metrics_path, calib_path = s.artifact_dir / "metrics.json", s.artifact_dir / "calibration.json"
    metrics, calib = json.loads(metrics_path.read_text()), json.loads(calib_path.read_text())
    before = metrics.get("anomaly", {})

    model_path = s.artifact_dir / "anomaly_model.joblib"
    if model_path.exists():
        shutil.copy(model_path, s.artifact_dir / "anomaly_model.previous.joblib")      # one step of undo

    print("Training the Isolation Forest (min log spread =", anom.MIN_LOG_SPREAD, ") ...")
    ad, thr = anom.fit(daily, agents, train_end, s)
    after = anom.evaluate(ad, thr, t["labels"], test_start)

    metrics["anomaly"] = after
    calib["thresholds_anomaly"] = thr
    metrics_path.write_text(json.dumps(metrics, indent=2, default=float))
    calib_path.write_text(json.dumps(calib, indent=2))
    run_id = run_with_conn(lambda db: insert_model_run(db, metrics, calib))

    def pct(x):
        return "n/a" if x is None else f"{x:.1%}"
    print("\n                       before     after")
    print(f"AUC (agent-day)      {before.get('roc_auc_agent_day', float('nan')):8.3f}  {after['roc_auc_agent_day']:8.3f}")
    print(f"precision            {pct(before.get('precision_at_threshold')):>8}  {pct(after['precision_at_threshold']):>8}")
    print(f"recall               {pct(before.get('recall_at_threshold')):>8}  {pct(after['recall_at_threshold']):>8}")
    print(f"false alerts / day   {before.get('false_alerts_per_day', float('nan')):8.1f}  {after['false_alerts_per_day']:8.1f}")
    print(f"episodes caught      {before.get('episode_detection_rate', float('nan')):8.2f}  {after['episodes_caught']:>8}   by type: {after['episode_detection_by_type']}")
    print(f"\nSaved model run #{run_id}. Restart the API to use the new model.")


if __name__ == "__main__":
    main()