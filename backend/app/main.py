from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import Ctx
from app.api.routes import router
from app.core.config import get_settings
from app.db.pool import create_pool
from app.services.anomaly_service import AnomalyService
from app.services.brief_service import BriefService
from app.services.liquidity_service import LiquidityService
from app.services.llm_service import LLMService
from app.services.store import AlertStore, DataStore
from app.api.routes_agent_intel import router as agent_intel_router
from app.services.agent_intel_service import AgentIntelService
from app.api.routes_copilot import router as copilot_router
from app.api.routes_coverage import router as coverage_router
from app.services.copilot_service import CopilotService
from app.services.coverage_service import CoverageService

from fastapi import Depends

from app.auth.deps import login_required

from app.api.routes_auth import router as auth_router
from app.api.routes_dashboard import router as dashboard_router

from app.services.dashboard_service import DashboardService



@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
   # fail fast if the schema is behind
    pool = await create_pool()
    try:
        store = await DataStore.create(pool)
        alerts = AlertStore(pool)
        liq = LiquidityService(store, s)
        anom = await asyncio.to_thread(AnomalyService, store, s, alerts)
        llm = LLMService(s)
        app.state.ctx = Ctx(s, pool, store, alerts, liq, anom, llm, BriefService(liq, anom, llm))
        app.state.agent_intel = await AgentIntelService.create(
            pool,
            store.agents,
            s,
        )
        app.state.coverage = CoverageService(
            pool,
            store,
            s.demo_as_of,
            s.commission_rate,
        )
        app.state.copilot = CopilotService(
            s,
            liq,
            anom,
            app.state.ctx.brief,
            getattr(app.state, "agent_intel", None),
            getattr(app.state, "coverage", None),
        )
        app.state.dashboard = DashboardService(
            app.state.ctx,
            getattr(app.state, "agent_intel", None),
            getattr(app.state, "coverage", None),
        )
        
        await liq.assess()          # warm the cache for the demo date
        yield
    finally:
        await pool.close()


app = FastAPI(title="upay Pulse - Agent Liquidity & Risk Intelligence", version="0.2.0", lifespan=lifespan,
              description="Track 05 (Merchant & Agent Intelligence). Synthetic data only. Forecasts and alerts are advisory.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
protected = [Depends(login_required)]
app.include_router(auth_router)
app.include_router(router, dependencies=protected)

app.include_router(
    agent_intel_router,
    dependencies=protected,
)

app.include_router(
    coverage_router,
    dependencies=protected,
)

app.include_router(
    copilot_router,
    dependencies=protected,
)

app.include_router(dashboard_router)