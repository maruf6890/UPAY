"""Raw-SQL data access helpers (asyncpg). Accept either an asyncpg Pool or Connection."""
from __future__ import annotations

import io
from typing import Sequence

import pandas as pd

TABLE_ORDER = ["agents", "hourly", "daily", "weather", "anomaly_labels"]
COLUMNS = {
    "agents": ["agent_id", "agent_code", "division", "district", "archetype", "area_type", "lat", "lon", "base_rate",
               "avg_txn_size", "out_share", "haat_day1", "haat_day2", "growth", "cash_target", "float_target"],
    "hourly": ["agent_id", "timestamp", "cash_out_cnt", "cash_in_cnt", "cash_out_amt", "cash_in_amt", "cash_balance",
               "float_balance", "stockout", "unserved_amt"],
    "daily": ["agent_id", "date", "txn_count", "out_amt", "in_amt", "avg_txn_size", "out_in_ratio", "peak_hour_share",
              "near_threshold_share", "repeat_counterparty_share", "night_txn_cnt", "round_amount_share",
              "is_anomaly", "anomaly_type"],
    "weather": ["date", "division", "rain_mm", "rain_3d"],
    "anomaly_labels": ["agent_id", "start_date", "end_date", "type", "strength"],
}


# ------------------------------------------------------------------ DataFrame <-> PostgreSQL
async def copy_df(db, table: str, df: pd.DataFrame, chunk: int = 200_000) -> None:
    """Bulk load with COPY ... FORMAT CSV (fast path: ~2M rows in about a minute)."""
    cols = COLUMNS[table]
    for i in range(0, len(df), chunk):
        csv = df.iloc[i:i + chunk][cols].to_csv(index=False, header=False)
        await db.copy_to_table(table, source=io.BytesIO(csv.encode()), columns=cols, format="csv")


async def fetch_df(db, query: str, *args, parse_dates: Sequence[str] = (), big: bool = False) -> pd.DataFrame:
    """big=True streams the result through COPY ... TO STDOUT (much faster than building Records for 100k+ rows)."""
    if big:
        buf = io.BytesIO()
        await db.copy_from_query(query, *args, output=buf, format="csv", header=True)
        buf.seek(0)
        return pd.read_csv(buf, parse_dates=list(parse_dates), true_values=["t"], false_values=["f"])
    rows = await db.fetch(query, *args)
    df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    for c in parse_dates:
        if c in df:
            df[c] = pd.to_datetime(df[c])
    return df


async def save_tables(db, t: dict, log=print) -> None:
    """Replace all synthetic data (operational tables such as alert_reviews are NOT touched)."""
    await db.execute("TRUNCATE agents, hourly, daily, weather, anomaly_labels RESTART IDENTITY CASCADE")
    frames = {"agents": t["agents"], "hourly": t["hourly"], "daily": t["daily"], "weather": t["weather"],
              "anomaly_labels": t["labels"].rename(columns={"start": "start_date", "end": "end_date"})}
    for name in TABLE_ORDER:
        await copy_df(db, name, frames[name])
        log(f"  loaded {name}: {len(frames[name]):,} rows")
    await db.execute("ANALYZE")


async def load_all(db) -> dict:
    t = {
        "agents": await fetch_df(db, "SELECT * FROM agents ORDER BY agent_id"),
        "hourly": await fetch_df(db, f"SELECT {', '.join(chr(34) + c + chr(34) for c in COLUMNS['hourly'])} "
                                     "FROM hourly ORDER BY agent_id, \"timestamp\"", parse_dates=["timestamp"], big=True),
        "daily": await fetch_df(db, "SELECT * FROM daily ORDER BY agent_id, date", parse_dates=["date"], big=True),
        "weather": await fetch_df(db, "SELECT * FROM weather ORDER BY division, date", parse_dates=["date"], big=True),
        "labels": await fetch_df(db, "SELECT agent_id, start_date AS start, end_date AS \"end\", type, strength FROM anomaly_labels",
                                 parse_dates=["start", "end"]),
    }
    return t


async def has_data(db) -> bool:
    try:
        return (await db.fetchval("SELECT count(*) FROM agents")) > 0
    except Exception:
        return False


# ------------------------------------------------------------------ operational tables
async def log_audit(db, actor: str, action: str, detail: dict) -> None:
    await db.execute("INSERT INTO audit_log (actor, action, detail) VALUES ($1, $2, $3)", actor, action, detail)


async def insert_model_run(db, metrics: dict, calibration: dict) -> int:
    import json
    clean = json.loads(json.dumps(metrics, default=float))
    return await db.fetchval("INSERT INTO model_runs (metrics, calibration) VALUES ($1, $2) RETURNING id", clean, calibration)


async def latest_model_run(db) -> dict | None:
    r = await db.fetchrow("SELECT id, created_at, metrics, calibration FROM model_runs ORDER BY id DESC LIMIT 1")
    return dict(r) if r else None
