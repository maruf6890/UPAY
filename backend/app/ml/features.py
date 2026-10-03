"""Feature engineering for the hourly liquidity model.

LEAKAGE RULE: a forecast issued at time s covers hours t in [s, s+24h). Every feature for target hour t
only uses information that is >= 24h older than t (same-hour lags of 1..7 days, and daily rolling means shifted 2 days),
or deterministic knowledge (calendar, agent profile, weather forecast). Rows exist only for the 16 open hours,
so "1 day" == 16 rows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.constants import ARCH_CODES, AREA_CODES, N_OPEN, OPEN_HOURS
from app.data.calendar_bd import build_calendar

FEATURES = [
    # calendar
    "hour", "dow", "dom", "is_friday", "is_salary_week", "is_remit_window", "is_ramadan",
    "is_eid_holiday", "days_to_eid", "days_since_eid",
    # agent profile / weather
    "is_haat_day", "rain_mm", "rain_3d", "arch_code", "area_code", "out_share",
    # history (normalised by the agent's typical hourly flow)
    "net_lag_1d", "net_lag_2d", "net_lag_7d", "out_lag_1d", "in_lag_1d",
    "net_mean_7d", "net_std_7d", "gross_mean_7d", "net_day_mean_14d", "gross_day_mean_14d",
]
CATEGORICAL = ["arch_code", "area_code"]


def compute_scale(hourly: pd.DataFrame, upto: pd.Timestamp | None = None) -> pd.Series:
    """Typical gross flow per open hour for each agent (used to normalise targets/features)."""
    h = hourly if upto is None else hourly[hourly.timestamp < upto + pd.Timedelta(days=1)]
    gross = h.cash_out_amt.astype("float64") + h.cash_in_amt.astype("float64")
    return gross.groupby(h.agent_id).mean().clip(lower=1.0).rename("scale")


def build_feature_frame(hourly: pd.DataFrame, agents: pd.DataFrame, weather: pd.DataFrame,
                        scale: pd.Series, pad_days: int = 0) -> pd.DataFrame:
    """hourly must contain WHOLE days (16 rows per agent per day). pad_days appends future rows (NaN demand)."""
    df = hourly[["agent_id", "timestamp", "cash_out_amt", "cash_in_amt"]].rename(
        columns={"cash_out_amt": "out", "cash_in_amt": "inn"}).copy()
    df[["out", "inn"]] = df[["out", "inn"]].astype("float64")
    if pad_days:
        last = df.timestamp.max().normalize()
        days = pd.date_range(last + pd.Timedelta(days=1), periods=pad_days, freq="D")
        ts = (days.values.astype("datetime64[ns]")[:, None] + np.array(OPEN_HOURS, dtype="timedelta64[h]")[None, :]).ravel()
        ids = df.agent_id.unique()
        fut = pd.DataFrame({"agent_id": np.repeat(ids, len(ts)), "timestamp": np.tile(ts, len(ids))})
        df = pd.concat([df, fut], ignore_index=True)
    df = df.sort_values(["agent_id", "timestamp"]).reset_index(drop=True)
    df["date"] = df.timestamp.dt.normalize()
    df["hour"] = df.timestamp.dt.hour.astype("int8")
    df["net"] = df.out - df.inn
    df["gross"] = df.out + df.inn
    df["scale"] = df.agent_id.map(scale).astype("float64")

    g = df.groupby("agent_id", sort=False)
    lag_net = pd.concat([g["net"].shift(N_OPEN * k) for k in range(1, 8)], axis=1)
    lag_gross = pd.concat([g["gross"].shift(N_OPEN * k) for k in range(1, 8)], axis=1)
    sc = df["scale"].values
    f = pd.DataFrame(index=df.index)
    f["net_lag_1d"] = lag_net.iloc[:, 0] / sc
    f["net_lag_2d"] = lag_net.iloc[:, 1] / sc
    f["net_lag_7d"] = lag_net.iloc[:, 6] / sc
    f["out_lag_1d"] = g["out"].shift(N_OPEN).values / sc
    f["in_lag_1d"] = g["inn"].shift(N_OPEN).values / sc
    full7 = lag_net.notna().all(axis=1)
    f["net_mean_7d"] = lag_net.mean(axis=1).where(full7) / sc
    f["net_std_7d"] = lag_net.std(axis=1).where(full7) / sc
    f["gross_mean_7d"] = lag_gross.mean(axis=1).where(full7) / sc

    daily = df.groupby(["agent_id", "date"], sort=True)[["net", "gross"]].sum(min_count=1).reset_index()
    roll = daily.groupby("agent_id")[["net", "gross"]].transform(lambda x: x.rolling(14, min_periods=7).mean().shift(2))
    daily["net_day_mean_14d"] = roll["net"]
    daily["gross_day_mean_14d"] = roll["gross"]
    df = pd.concat([df, f], axis=1).merge(
        daily[["agent_id", "date", "net_day_mean_14d", "gross_day_mean_14d"]], on=["agent_id", "date"], how="left")
    df["net_day_mean_14d"] = df["net_day_mean_14d"] / (df["scale"] * N_OPEN)
    df["gross_day_mean_14d"] = df["gross_day_mean_14d"] / (df["scale"] * N_OPEN)

    cal = build_calendar(df.date.unique())
    ag = agents[["agent_id", "division", "archetype", "area_type", "out_share", "haat_day1", "haat_day2"]]
    df = df.merge(cal, on="date", how="left").merge(ag, on="agent_id", how="left")
    df["is_haat_day"] = ((df.dow == df.haat_day1) | (df.dow == df.haat_day2)).astype("int8")
    df["arch_code"] = df.archetype.map(ARCH_CODES).astype("int8")
    df["area_code"] = df.area_type.map(AREA_CODES).astype("int8")
    df = df.merge(weather[["date", "division", "rain_mm", "rain_3d"]], on=["date", "division"], how="left")
    df[["rain_mm", "rain_3d"]] = df[["rain_mm", "rain_3d"]].fillna(0.0)
    df["y"] = df["net"] / df["scale"]
    df[FEATURES] = df[FEATURES].astype("float32")
    keep = ["agent_id", "timestamp", "date", "scale", "net", "out", "inn", "y",
            "archetype", "area_type", "division"] + FEATURES
    df = df[keep]
    for c in ("scale", "net", "out", "inn", "y"):
        df[c] = df[c].astype("float32")
    for c in ("archetype", "area_type", "division"):
        df[c] = df[c].astype("category")
    return df.sort_values(["agent_id", "timestamp"]).reset_index(drop=True)


def build_feature_frame_chunked(hourly, agents, weather, scale, pad_days: int = 0, chunk: int = 60) -> pd.DataFrame:
    """Same as build_feature_frame but processes agents in chunks to keep peak memory low."""
    ids = np.sort(hourly.agent_id.unique())
    parts = []
    for i in range(0, len(ids), chunk):
        sel = ids[i:i + chunk]
        parts.append(build_feature_frame(hourly[hourly.agent_id.isin(sel)], agents, weather, scale, pad_days))
    out = pd.concat(parts, ignore_index=True)
    for c in ("archetype", "area_type", "division"):
        out[c] = out[c].astype("category")
    return out


def valid_mask(frame: pd.DataFrame) -> pd.Series:
    return frame[FEATURES].notna().all(axis=1) & frame["y"].notna()


def to_cube(frame: pd.DataFrame, col: str, n_agents: int | None = None) -> np.ndarray:
    """frame sorted by (agent, timestamp) with whole days -> array (A, D, 16)."""
    a = frame.agent_id.nunique() if n_agents is None else n_agents
    v = frame[col].to_numpy()
    return v.reshape(a, -1, N_OPEN)
