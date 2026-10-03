"""asyncpg connection helpers (raw SQL, no ORM)."""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable, TypeVar

import asyncpg

from app.core.config import get_settings

T = TypeVar("T")


async def _init(conn: asyncpg.Connection) -> None:
    for t in ("jsonb", "json"):
        await conn.set_type_codec(t, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def create_pool(min_size: int = 1, max_size: int = 10) -> asyncpg.Pool:
    return await asyncpg.create_pool(get_settings().dsn, min_size=min_size, max_size=max_size, init=_init, command_timeout=300)


async def connect() -> asyncpg.Connection:
    c = await asyncpg.connect(get_settings().dsn, command_timeout=900)
    await _init(c)
    return c


def run_with_conn(fn: Callable[[asyncpg.Connection], Awaitable[T]]) -> T:
    """Sync helper for scripts / the training pipeline: open a connection, run `fn(conn)`, close."""
    async def _go() -> T:
        c = await connect()
        try:
            return await fn(c)
        finally:
            await c.close()
    return asyncio.run(_go())
