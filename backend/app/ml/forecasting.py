"""LightGBM quantile models (P10 / P50 / P90) for hourly net cash flow + the 7-day moving-average baseline."""
from __future__ import annotations

import json

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from app.core.config import Settings
from app.core.constants import QUANTILES, Z90
from app.ml.features import CATEGORICAL, FEATURES, valid_mask

PARAMS = dict(
    objective="quantile", learning_rate=0.06, num_leaves=63, min_data_in_leaf=300,
    feature_fraction=0.8, bagging_fraction=0.7, bagging_freq=1, lambda_l2=1.0, verbose=-1, seed=42,
)


def train_quantile_models(frame: pd.DataFrame, train_end: pd.Timestamp, val_end: pd.Timestamp,
                          s: Settings, log=print) -> dict[str, lgb.Booster]:
    ok = valid_mask(frame)
    tr = frame[ok & (frame.date <= train_end)]
    va = frame[ok & (frame.date > train_end) & (frame.date <= val_end)]
    if s.train_sample_frac < 1:
        tr = tr.sample(frac=s.train_sample_frac, random_state=s.seed)
    va = va.sample(n=min(len(va), 100_000), random_state=s.seed)
    log(f"Training rows: {len(tr):,} | early-stopping rows: {len(va):,}")
    tr = tr[FEATURES + ["y"]].copy()
    va = va[FEATURES + ["y"]].copy()
    models = {}
    for name, alpha in QUANTILES.items():
        dtr = lgb.Dataset(tr[FEATURES], tr["y"], categorical_feature=CATEGORICAL, free_raw_data=False)
        dva = lgb.Dataset(va[FEATURES], va["y"], reference=dtr, categorical_feature=CATEGORICAL)
        m = lgb.train({**PARAMS, "alpha": alpha}, dtr, num_boost_round=s.n_estimators, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(40, verbose=False)])
        log(f"  {name}: best_iteration={m.best_iteration}")
        models[name] = m
    return models


def predict_quantiles(models: dict[str, lgb.Booster], frame: pd.DataFrame) -> pd.DataFrame:
    """Returns q10/q50/q90 in BDT (de-normalised), sorted so quantiles never cross."""
    X = frame[FEATURES]
    raw = np.stack([models[k].predict(X, num_iteration=models[k].best_iteration) for k in ("q10", "q50", "q90")], axis=1)
    raw = np.sort(raw, axis=1) * frame["scale"].to_numpy()[:, None]
    return pd.DataFrame(raw, columns=["q10", "q50", "q90"], index=frame.index)


def baseline_quantiles(frame: pd.DataFrame) -> pd.DataFrame:
    """Status-quo rule: mean of the same hour over the previous 7 days, with a +/- z90*std band."""
    sc = frame["scale"].to_numpy()
    mu = frame["net_mean_7d"].to_numpy() * sc
    sd = frame["net_std_7d"].to_numpy() * sc
    return pd.DataFrame({"q10": mu - Z90 * sd, "q50": mu, "q90": mu + Z90 * sd}, index=frame.index)


def save_artifacts(models, scale: pd.Series, calib: dict, s: Settings) -> None:
    d = s.artifact_dir
    d.mkdir(parents=True, exist_ok=True)
    joblib.dump({k: m.model_to_string() for k, m in models.items()}, d / "liquidity_models.joblib")
    scale.to_frame("scale").to_parquet(d / "agent_scale.parquet")
    (d / "calibration.json").write_text(json.dumps(calib, indent=2))


def load_artifacts(s: Settings):
    d = s.artifact_dir
    raw = joblib.load(d / "liquidity_models.joblib")
    models = {k: lgb.Booster(model_str=v) for k, v in raw.items()}
    scale = pd.read_parquet(d / "agent_scale.parquet")["scale"]
    calib = json.loads((d / "calibration.json").read_text())
    return models, scale, calib
