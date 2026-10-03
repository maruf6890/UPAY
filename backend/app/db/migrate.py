"""Versioned SQL migration runner for asyncpg.

* Files live in app/db/migrations as  NNNN_name.sql  with two sections:
      -- migrate:up
      ...
      -- migrate:down
      ...
* Applied versions are recorded in  schema_migrations (version, name, checksum, applied_at, execution_ms).
* Each migration runs inside its own transaction. A PostgreSQL advisory lock stops two runners racing.
* Drift protection: if an applied migration file was edited afterwards (checksum differs) the runner refuses to continue.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path

import asyncpg

from app.db.pool import connect

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
LOCK_ID = 727_272_001
UP, DOWN = "-- migrate:up", "-- migrate:down"
FILE_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version      INTEGER PRIMARY KEY,
    name         TEXT        NOT NULL,
    checksum     TEXT        NOT NULL,
    applied_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    execution_ms INTEGER     NOT NULL DEFAULT 0
)"""


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up: str
    down: str
    checksum: str
    path: Path


def load_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    out, seen = [], set()
    for p in sorted(directory.glob("*.sql")):
        m = FILE_RE.match(p.name)
        if not m:
            raise MigrationError(f"Bad migration file name '{p.name}' (expected 0001_description.sql)")
        version = int(m.group(1))
        if version in seen:
            raise MigrationError(f"Duplicate migration version {version:04d}")
        seen.add(version)
        text = p.read_text(encoding="utf-8").replace("\r\n", "\n")
        if UP not in text:
            raise MigrationError(f"{p.name} is missing the '{UP}' marker")
        head, _, rest = text.partition(UP)
        up, _, down = rest.partition(DOWN)
        out.append(Migration(version, m.group(2), up.strip(), down.strip(),
                             hashlib.sha256(text.encode()).hexdigest(), p))
    return out


async def _prepare(conn: asyncpg.Connection) -> dict[int, asyncpg.Record]:
    await conn.fetchval("SELECT pg_advisory_lock($1)", LOCK_ID)
    await conn.execute(CREATE_TABLE)
    rows = await conn.fetch("SELECT * FROM schema_migrations ORDER BY version")
    return {r["version"]: r for r in rows}


def _check_drift(migs: list[Migration], done: dict) -> None:
    by_v = {m.version: m for m in migs}
    for v, r in done.items():
        if v not in by_v:
            raise MigrationError(f"Version {v:04d} ({r['name']}) is applied in the database but its file is missing")
        if by_v[v].checksum != r["checksum"]:
            raise MigrationError(f"Migration {v:04d}_{r['name']} was modified after it was applied. "
                                 f"Never edit an applied migration - create a new one: python3 -m scripts.migrate new <name>")


async def status(conn: asyncpg.Connection | None = None) -> list[dict]:
    own = conn is None
    conn = conn or await connect()
    try:
        done = await _prepare(conn)
        migs = load_migrations()
        by_v = {m.version: m for m in migs}
        rows = []
        for m in migs:
            if m.version in done:
                state = "applied" if done[m.version]["checksum"] == m.checksum else "MODIFIED"
                rows.append(dict(version=m.version, name=m.name, state=state, applied_at=done[m.version]["applied_at"]))
            else:
                rows.append(dict(version=m.version, name=m.name, state="pending", applied_at=None))
        for v, r in done.items():
            if v not in by_v:
                rows.append(dict(version=v, name=r["name"], state="MISSING FILE", applied_at=r["applied_at"]))
        return rows
    finally:
        if own:
            await conn.close()


async def up(to: int | None = None, log=print) -> int:
    conn = await connect()
    try:
        done = await _prepare(conn)
        migs = load_migrations()
        _check_drift(migs, done)
        newest = max(done, default=0)
        pending = [m for m in migs if m.version not in done and (to is None or m.version <= to)]
        for m in pending:
            if m.version < newest:
                raise MigrationError(f"Out-of-order migration {m.version:04d}: a newer version ({newest:04d}) is already applied")
        for m in pending:
            t0 = time.perf_counter()
            async with conn.transaction():
                await conn.execute(m.up)
                ms = int((time.perf_counter() - t0) * 1000)
                await conn.execute("INSERT INTO schema_migrations (version, name, checksum, execution_ms) VALUES ($1,$2,$3,$4)",
                                   m.version, m.name, m.checksum, ms)
            log(f"  applied  {m.version:04d}_{m.name}  ({ms} ms)")
        if not pending:
            log("  database is up to date")
        return len(pending)
    finally:
        await conn.close()


async def down(steps: int = 1, to: int | None = None, log=print) -> int:
    """Roll back the newest `steps` migrations, or everything newer than version `to`."""
    conn = await connect()
    try:
        done = await _prepare(conn)
        migs = {m.version: m for m in load_migrations()}
        _check_drift(list(migs.values()), done)
        targets = sorted(done, reverse=True)
        targets = [v for v in targets if v > to] if to is not None else targets[:steps]
        for v in targets:
            m = migs[v]
            if not m.down:
                raise MigrationError(f"Migration {v:04d}_{m.name} has no '{DOWN}' section - it is irreversible")
            t0 = time.perf_counter()
            async with conn.transaction():
                await conn.execute(m.down)
                await conn.execute("DELETE FROM schema_migrations WHERE version = $1", v)
            log(f"  reverted {v:04d}_{m.name}  ({int((time.perf_counter() - t0) * 1000)} ms)")
        if not targets:
            log("  nothing to revert")
        return len(targets)
    finally:
        await conn.close()


async def ensure_current(auto: bool = False, log=print) -> None:
    """Used by the API at startup: fail fast (or auto-apply) when migrations are pending."""
    rows = await status()
    bad = [r for r in rows if r["state"] in ("MODIFIED", "MISSING FILE")]
    if bad:
        raise MigrationError(f"Migration drift detected: {[(r['version'], r['state']) for r in bad]}")
    if any(r["state"] == "pending" for r in rows):
        if auto:
            log("AUTO_MIGRATE=true -> applying pending migrations")
            await up(log=log)
        else:
            raise MigrationError("Database schema is not up to date. Run:  python3 -m scripts.migrate up")


def new_migration(name: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug:
        raise MigrationError("Give the migration a name, e.g.  new add_risk_snapshots")
    nxt = max((m.version for m in load_migrations()), default=0) + 1
    path = MIGRATIONS_DIR / f"{nxt:04d}_{slug}.sql"
    path.write_text(f"{UP}\n-- write the forward change here\n\n\n{DOWN}\n-- write how to undo it here\n", encoding="utf-8")
    return path
