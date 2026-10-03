"""Load the synthetic tables from PostgreSQL (sync wrapper for scripts / the training pipeline)."""
from __future__ import annotations

from app.core.config import Settings
from app.db import queries as q
from app.db.pool import run_with_conn


def load_tables(settings: Settings | None = None) -> dict:
    async def go(db):
        if not await q.has_data(db):
            raise RuntimeError("PostgreSQL has no data. Run: python3 -m scripts.generate_data")
        return await q.load_all(db)
    return run_with_conn(go)
