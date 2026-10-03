"""Async PostgreSQL-backed data access + alert review store (raw SQL via asyncpg)."""
from __future__ import annotations

import asyncpg
import pandas as pd

from app.db import queries as q


class DataStore:
    """Small tables are cached in memory; the big hourly table is queried by time window (indexed)."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def create(cls, pool: asyncpg.Pool) -> "DataStore":
        self = cls(pool)
        self.agents = await q.fetch_df(pool, "SELECT * FROM agents ORDER BY agent_id")
        self.daily = await q.fetch_df(pool, "SELECT * FROM daily ORDER BY agent_id, date", parse_dates=["date"], big=True)
        self.weather = await q.fetch_df(pool, "SELECT * FROM weather", parse_dates=["date"], big=True)
        self.labels = await q.fetch_df(pool, "SELECT * FROM anomaly_labels")
        lo, hi = await pool.fetchrow('SELECT min("timestamp"), max("timestamp") FROM hourly')
        if lo is None:
            raise RuntimeError("hourly table is empty. Run: python3 -m scripts.generate_data")
        self.data_start, self.data_end = pd.Timestamp(lo), pd.Timestamp(hi)
        self.agent_ids = self.agents.agent_id.to_numpy()
        return self

    async def hourly_window(self, start, end, agent_id: int | None = None) -> pd.DataFrame:
        """Rows with start <= timestamp < end (optionally one agent), sorted by agent, time."""
        cols = ('agent_id, "timestamp", cash_out_cnt, cash_in_cnt, cash_out_amt, cash_in_amt, '
                'cash_balance, float_balance, stockout, unserved_amt')
        a, b = pd.Timestamp(start).to_pydatetime(), pd.Timestamp(end).to_pydatetime()
        if agent_id is None:
            sql, args = f'SELECT {cols} FROM hourly WHERE "timestamp" >= $1 AND "timestamp" < $2 ORDER BY agent_id, "timestamp"', (a, b)
        else:
            sql, args = (f'SELECT {cols} FROM hourly WHERE "timestamp" >= $1 AND "timestamp" < $2 AND agent_id = $3 '
                         'ORDER BY "timestamp"'), (a, b, int(agent_id))
        return await q.fetch_df(self.pool, sql, *args, parse_dates=["timestamp"], big=True)

    def agent_row(self, agent_id: int) -> pd.Series:
        r = self.agents[self.agents.agent_id == agent_id]
        if r.empty:
            raise KeyError(f"agent {agent_id} not found")
        return r.iloc[0]


def _rev(r: asyncpg.Record) -> dict:
    return dict(status=r["status"], reviewer=r["reviewer"], note=r["note"], reviewed_at=r["reviewed_at"].isoformat())


class AlertStore:
    """Human-in-the-loop review log. alert_reviews = current state; feedback_log = append-only history
    (every decision becomes a future training label); audit_log records who did what. All three writes are ONE transaction."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get(self, alert_id: str) -> dict | None:
        r = await self.pool.fetchrow("SELECT * FROM alert_reviews WHERE alert_id = $1", alert_id)
        return _rev(r) if r else None

    async def get_many(self, ids: list[str]) -> dict[str, dict]:
        if not ids:
            return {}
        rows = await self.pool.fetch("SELECT * FROM alert_reviews WHERE alert_id = ANY($1::text[])", ids)
        return {r["alert_id"]: _rev(r) for r in rows}

    async def review(self, alert_id: str, decision: str, reviewer: str, note: str | None) -> dict:
        async with self.pool.acquire() as c, c.transaction():
            await c.execute(
                """INSERT INTO alert_reviews (alert_id, status, reviewer, note) VALUES ($1, $2, $3, $4)
                   ON CONFLICT (alert_id) DO UPDATE
                   SET status = EXCLUDED.status, reviewer = EXCLUDED.reviewer, note = EXCLUDED.note, reviewed_at = now()""",
                alert_id, decision, reviewer, note)
            await c.execute("INSERT INTO feedback_log (alert_id, decision, reviewer, note) VALUES ($1,$2,$3,$4)",
                            alert_id, decision, reviewer, note)
            await q.log_audit(c, reviewer, "alert_review", {"alert_id": alert_id, "decision": decision})
        return await self.get(alert_id)
