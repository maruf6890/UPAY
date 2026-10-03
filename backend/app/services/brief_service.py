"""Builds the grounded facts for the manager's daily brief, then asks the LLM layer to write it up."""
from __future__ import annotations

from app.core.utils import fmt_time
from app.ml.rebalance import plan_route
from app.services.anomaly_service import AnomalyService
from app.services.liquidity_service import LiquidityService
from app.services.llm_service import LLMService


class BriefService:
    def __init__(self, liq: LiquidityService, anom: AnomalyService, llm: LLMService):
        self.liq, self.anom, self.llm = liq, anom, llm

    async def build_facts(self, as_of=None, district: str | None = None) -> dict:
        res = await self.liq.assess(as_of)
        risk = await self.liq.risk_table(res["as_of"], district)
        counts = risk.risk_level.value_counts().to_dict()
        counts = {k: int(counts.get(k, 0)) for k in ("HIGH", "MEDIUM", "LOW")}
        route = plan_route(risk)
        top = []
        for _, r in risk.head(5).iterrows():
            drv = (await self.liq.agent_forecast(int(r.agent_id), res["as_of"], include_history=False))["drivers"]
            top.append(dict(agent_code=r.agent_code, district=r.district, archetype=r.archetype, risk_side=r.risk_side,
                            stockout_prob=float(r.stockout_prob), cash_topup_bdt=float(r.cash_topup_bdt),
                            float_topup_bdt=float(r.float_topup_bdt), expected_stockout=fmt_time(r.p50_stockout_time),
                            top_driver=drv[0]["text_en"] if drv else "n/a"))
        al = await self.anom.alerts_for(res["as_of"], status="pending")
        if district:
            al = [a for a in al if a["district"].lower() == district.lower()]
        return dict(
            as_of=str(res["as_of"]), scope=district or "all districts", counts=counts, n_agents=int(len(risk)),
            total_cash_needed_bdt=float(risk[risk.risk_level.isin(["HIGH", "MEDIUM"])].cash_topup_bdt.sum()),
            top_risk_agents=top,
            anomaly_alerts_pending=len(al),
            top_anomaly_alerts=[dict(agent_code=a["agent_code"], severity=a["severity"],
                                     signals=[x["label"] for x in a["reasons"]]) for a in al[:3]],
            route=dict(stops=len(route["stops"]), total_km=route["total_km"], cash_to_carry_bdt=route["total_cash_bdt"]),
        )

    async def brief(self, as_of=None, district: str | None = None) -> dict:
        facts = await self.build_facts(as_of, district)
        return {"facts": facts, "brief": await self.llm.brief(facts)}
