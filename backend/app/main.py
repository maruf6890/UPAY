from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import Ctx
from app.api.routes import router
from app.core.config import get_settings
from app.db import migrate
from app.db.pool import create_pool
from app.services.anomaly_service import AnomalyService
from app.services.brief_service import BriefService
from app.services.liquidity_service import LiquidityService
from app.services.llm_service import LLMService
from app.services.store import AlertStore, DataStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    await migrate.ensure_current(auto=s.auto_migrate)        # fail fast if the schema is behind
    pool = await create_pool()
    try:
        store = await DataStore.create(pool)
        alerts = AlertStore(pool)
        liq = LiquidityService(store, s)
        anom = await asyncio.to_thread(AnomalyService, store, s, alerts)
        llm = LLMService(s)
        app.state.ctx = Ctx(s, pool, store, alerts, liq, anom, llm, BriefService(liq, anom, llm))
        await liq.assess()          # warm the cache for the demo date
        yield
    finally:
        await pool.close()


app = FastAPI(title="upay Pulse - Agent Liquidity & Risk Intelligence", version="0.2.0", lifespan=lifespan,
              description="Track 05 (Merchant & Agent Intelligence). Synthetic data only. Forecasts and alerts are advisory.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
