"""API routes for B4 (performance intelligence) and B7 (churn prediction).

All routes live under /intel. The service object is created in app/main.py and stored in
app.state.agent_intel. The combined 'overview' route also uses the EXISTING liquidity service
(app.state.ctx.liquidity), which is how the new features connect to the old ones.
"""
from fastapi import APIRouter, HTTPException, Query, Request

from app.core.constants import parse_agent_code
from app.core.utils import clean
from app.services.agent_intel_service import AgentIntelService

router = APIRouter(prefix="/intel", tags=["agent-intelligence"])

LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def get_service(request: Request) -> AgentIntelService:
    service = getattr(request.app.state, "agent_intel", None)
    if service is None:
        raise HTTPException(503, "Agent intelligence service is not loaded")
    return service


def get_agent_id(service: AgentIntelService, agent_code: str) -> int:
    try:
        agent_id = parse_agent_code(agent_code)
    except ValueError:
        raise HTTPException(400, "Invalid agent code, expected something like AG0007")
    if not service.has_agent(agent_id):
        raise HTTPException(404, f"Agent {agent_code} not found")
    return agent_id


def require_churn_model(service: AgentIntelService) -> None:
    if service.churn_model is None:
        raise HTTPException(503, "Churn model not trained yet. Run: python3 -m scripts.train_churn")


# ------------------------------------------------------------------ meta
@router.get("/weeks")
async def weeks(request: Request):
    """Which weeks exist and which one is used by default."""
    service = get_service(request)
    return clean(service.available_weeks())


# ------------------------------------------------------------------ B4: performance
@router.get("/performance/summary")
async def performance_summary(request: Request, as_of: str | None = None, district: str | None = None):
    service = get_service(request)
    try:
        return clean(service.performance_summary(as_of, district))
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.get("/performance/agents")
async def performance_agents(
    request: Request,
    as_of: str | None = None,
    district: str | None = None,
    segment: str | None = Query(None, pattern="^(DECLINING|SERVICE_GAP|EMERGING_HIGH_PERFORMER|TOP_PERFORMER|STEADY)$"),
    limit: int = Query(30, le=300),
):
    service = get_service(request)
    try:
        week_index, table = service.performance_table(as_of, district, segment)
    except ValueError as error:
        raise HTTPException(400, str(error))

    columns = ["agent_code", "district", "archetype", "performance_score", "segment", "flags", "cluster_name",
               "volume_percentile", "relative_growth", "stockout_rate_4w", "lost_volume_4w_bdt", "recommended_action"]
    return clean({
        "week_start": str(service.week_dates[week_index].date()),
        "total": int(len(table)),
        "agents": table[columns].head(limit),
    })


@router.get("/performance/agents/{agent_code}")
async def performance_agent(agent_code: str, request: Request, as_of: str | None = None):
    service = get_service(request)
    agent_id = get_agent_id(service, agent_code)
    try:
        detail = service.performance_agent(agent_id, as_of)
    except ValueError as error:
        raise HTTPException(400, str(error))
    return clean(detail)


# ------------------------------------------------------------------ B7: churn
@router.get("/churn/risk")
async def churn_risk(
    request: Request,
    as_of: str | None = None,
    district: str | None = None,
    level: str | None = Query(None, pattern="^(HIGH|MEDIUM|LOW|INACTIVE)$"),
    limit: int = Query(30, le=300),
):
    service = get_service(request)
    require_churn_model(service)
    try:
        week_index, table = service.churn_table(as_of)
    except ValueError as error:
        raise HTTPException(400, str(error))

    if district is not None:
        table = table[table["district"].str.lower() == district.lower()]

    level_counts = table["risk_level"].value_counts().to_dict()
    if level is not None:
        table = table[table["risk_level"] == level]

    columns = ["agent_code", "district", "archetype", "status", "churn_probability", "risk_level",
               "txn_ratio_4w", "stockout_hours_4w", "drivers", "recommended_action"]
    return clean({
        "week_start": str(service.week_dates[week_index].date()),
        "horizon_weeks": 4,
        "level_counts": level_counts,
        "agents": table[columns].head(limit),
    })


@router.get("/churn/agents/{agent_code}")
async def churn_agent(agent_code: str, request: Request, as_of: str | None = None):
    service = get_service(request)
    require_churn_model(service)
    agent_id = get_agent_id(service, agent_code)
    try:
        detail = service.churn_agent(agent_id, as_of)
    except ValueError as error:
        raise HTTPException(400, str(error))
    return clean(detail)


@router.get("/churn/metrics")
async def churn_metrics(request: Request):
    service = get_service(request)
    require_churn_model(service)
    return clean(service.churn_metrics)


# ------------------------------------------------------------------ combined view (uses the EXISTING liquidity service)
def combine_priority(liquidity_level, churn_level):
    """Business rule that joins the two risks into one priority for the area manager."""
    churn_rank = LEVEL_ORDER.get(churn_level, 0)
    liquidity_rank = LEVEL_ORDER.get(liquidity_level, 0)

    if churn_rank == 2 and liquidity_rank == 2:
        return "URGENT", "Likely to run out of money today AND likely to leave soon. Fix liquidity first, then call the agent."
    if churn_rank == 2 or liquidity_rank == 2:
        return "HIGH", "One serious risk. Handle it this week."
    if churn_rank == 1 or liquidity_rank == 1:
        return "MEDIUM", "Keep an eye on this agent."
    return "LOW", "No action needed."


@router.get("/agents/{agent_code}/overview")
async def agent_overview(agent_code: str, request: Request, as_of: str | None = None):
    """One call that joins liquidity risk (existing), churn risk (B7) and performance (B4)."""
    service = get_service(request)
    agent_id = get_agent_id(service, agent_code)
    context = request.app.state.ctx

    try:
        liquidity_time = context.liquidity.parse_as_of(as_of)
        liquidity_table = await context.liquidity.risk_table(liquidity_time)
        performance = service.performance_agent(agent_id, as_of)
    except ValueError as error:
        raise HTTPException(400, str(error))

    liquidity_row = liquidity_table[liquidity_table["agent_id"] == agent_id].iloc[0]
    liquidity = {
        "risk_level": liquidity_row["risk_level"],
        "risk_side": liquidity_row["risk_side"],
        "stockout_probability": float(liquidity_row["stockout_prob"]),
        "cash_topup_bdt": float(liquidity_row["cash_topup_bdt"]),
        "float_topup_bdt": float(liquidity_row["float_topup_bdt"]),
    }

    churn_detail = None
    churn_level = "LOW"
    if service.churn_model is not None:
        churn_detail = service.churn_agent(agent_id, as_of)
        churn_level = churn_detail["risk_level"]

    priority, message = combine_priority(liquidity["risk_level"], churn_level)
    return clean({
        "agent_code": agent_code.upper(),
        "liquidity_as_of": liquidity_time,
        "liquidity": liquidity,
        "churn": churn_detail,
        "performance": performance,
        "combined_priority": priority,
        "combined_message": message,
    })
