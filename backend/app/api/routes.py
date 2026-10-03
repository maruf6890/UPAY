from __future__ import annotations

import json

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import Ctx, get_ctx
from app.core.constants import parse_agent_code
from app.core.utils import clean
from app.ml.rebalance import plan_route
from app.schemas import ReviewRequest

router = APIRouter()


def _agent_id(ctx: Ctx, code: str) -> int:
    try:
        aid = parse_agent_code(code)
    except ValueError:
        raise HTTPException(400, "Invalid agent code, expected e.g. AG0007")
    if aid not in set(ctx.store.agent_ids.tolist()):
        raise HTTPException(404, f"Agent {code} not found")
    return aid


def _as_of(ctx: Ctx, as_of: str | None):
    try:
        return ctx.liquidity.parse_as_of(as_of)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ------------------------------------------------------------------ meta
@router.get("/health", tags=["meta"])
async def health(ctx: Ctx = Depends(get_ctx)):
    try:
        db = "up" if await ctx.pool.fetchval("SELECT 1") == 1 else "down"
    except Exception:
        db = "down"
    return {"status": "ok" if db == "up" else "degraded", "database": db,
            "llm": "gemini" if ctx.llm.enabled else "template-fallback", "llm_model": ctx.llm.model_name}


@router.get("/meta", tags=["meta"])
async def meta(ctx: Ctx = Depends(get_ctx)):
    st = ctx.store
    return clean(dict(default_as_of=ctx.liquidity.default_as_of(), data_start=st.data_start, data_end=st.data_end,
                      n_agents=len(st.agents), districts=sorted(st.agents.district.unique()), calibration=ctx.liquidity.calib,
                      stockout_definition="An hour with more than ৳2,000 of unserved demand (cash for cash-outs / e-float for cash-ins ran out)."))


@router.get("/metrics", tags=["meta"])
async def metrics(ctx: Ctx = Depends(get_ctx)):
    from app.db.queries import latest_model_run
    run = await latest_model_run(ctx.pool)
    if run:
        return clean(dict(model_run_id=run["id"], trained_at=run["created_at"], **run["metrics"]))
    p = ctx.settings.artifact_dir / "metrics.json"
    if not p.exists():
        raise HTTPException(404, "Run python -m scripts.train first")
    return json.loads(p.read_text())


# ------------------------------------------------------------------ agents
@router.get("/agents", tags=["agents"])
async def list_agents(district: str | None = None, archetype: str | None = None, limit: int = Query(50, le=500),
                ctx: Ctx = Depends(get_ctx)):
    a = ctx.store.agents
    if district:
        a = a[a.district.str.lower() == district.lower()]
    if archetype:
        a = a[a.archetype == archetype]
    cols = ["agent_code", "district", "division", "archetype", "area_type", "lat", "lon"]
    return clean(a[cols].head(limit))


@router.get("/agents/{code}/forecast", tags=["liquidity"])
async def agent_forecast(code: str, as_of: str | None = Query(None, description="e.g. 2026-05-25 07:00"), ctx: Ctx = Depends(get_ctx)):
    """24h P10/P50/P90 net-flow forecast, projected cash & e-float balances, stockout risk, top-up advice, SHAP drivers."""
    return clean(await ctx.liquidity.agent_forecast(_agent_id(ctx, code), _as_of(ctx, as_of)))


@router.get("/agents/{code}/anomaly", tags=["anomaly"])
async def agent_anomaly(code: str, days: int = 30, as_of: str | None = None, ctx: Ctx = Depends(get_ctx)):
    return clean(ctx.anomaly.score_history(_agent_id(ctx, code), days, _as_of(ctx, as_of)))


# ------------------------------------------------------------------ risk + rebalancing
@router.get("/risk", tags=["liquidity"])
async def risk(as_of: str | None = None, district: str | None = None, level: str | None = Query(None, pattern="^(HIGH|MEDIUM|LOW)$"),
         limit: int = Query(50, le=500), ctx: Ctx = Depends(get_ctx)):
    """Stockout-risk table for the manager console (sorted by probability)."""
    ts = _as_of(ctx, as_of)
    r = await ctx.liquidity.risk_table(ts, district)
    summary = {k: int((r.risk_level == k).sum()) for k in ("HIGH", "MEDIUM", "LOW")}
    if level:
        r = r[r.risk_level == level]
    drop = ["agent_id", "need_cash_p90", "need_float_p90"]
    return clean(dict(as_of=ts, summary=summary, agents=r.drop(columns=drop).head(limit)))


@router.get("/rebalance", tags=["liquidity"])
async def rebalance(as_of: str | None = None, district: str | None = None, van_capacity_bdt: float = 5_000_000,
              max_stops: int = Query(12, le=40), ctx: Ctx = Depends(get_ctx)):
    """Greedy DSO route: highest (risk x shortfall) first within van cash capacity, ordered nearest-neighbour."""
    ts = _as_of(ctx, as_of)
    r = await ctx.liquidity.risk_table(ts, district)
    return clean(dict(as_of=ts, district=district or "all", **plan_route(r, van_capacity_bdt, max_stops)))


# ------------------------------------------------------------------ alerts (human in the loop)
@router.get("/alerts", tags=["anomaly"])
async def alerts(as_of: str | None = None, status: str | None = Query(None, pattern="^(pending|confirmed|dismissed)$"),
           lookback_days: int = Query(3, ge=1, le=14), ctx: Ctx = Depends(get_ctx)):
    ts = _as_of(ctx, as_of)
    return clean(dict(as_of=ts, alerts=await ctx.anomaly.alerts_for(ts, lookback_days, status)))


@router.post("/alerts/{alert_id}/review", tags=["anomaly"])
async def review_alert(alert_id: str, body: ReviewRequest, ctx: Ctx = Depends(get_ctx)):
    try:
        await ctx.anomaly.get_alert(alert_id)
    except (KeyError, ValueError):
        raise HTTPException(404, "Alert not found")
    return clean(dict(alert_id=alert_id, **await ctx.alerts.review(alert_id, body.decision, body.reviewer, body.note)))


@router.get("/alerts/{alert_id}/narrative", tags=["anomaly"])
async def alert_narrative(alert_id: str, ctx: Ctx = Depends(get_ctx)):
    try:
        facts = await ctx.anomaly.get_alert(alert_id)
    except (KeyError, ValueError):
        raise HTTPException(404, "Alert not found")
    return clean(dict(alert_id=alert_id, **await ctx.llm.alert_narrative(clean(facts))))


# ------------------------------------------------------------------ AI brief
@router.get("/brief", tags=["copilot"])
async def daily_brief(as_of: str | None = None, district: str | None = None, ctx: Ctx = Depends(get_ctx)):
    """LangChain + Gemini morning brief, grounded ONLY in model outputs (falls back to a template without an API key)."""
    return clean(await ctx.brief.brief(_as_of(ctx, as_of), district))
