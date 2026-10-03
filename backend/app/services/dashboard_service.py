"""One dashboard, different data for each role.

The frontend calls GET /dashboard and draws the list of widgets it gets back.
What is in the list depends on the logged-in user's role:

  manager : cash/e-float risk, riskiest agents, delivery route, alerts, churn, performance, coverage gaps
            (limited to the manager's own district when the account has one)
  agent   : ONLY the agent's own status, advice, next-24-hour chart, reasons and recent activity
  analyst : alerts to review, review activity, model quality, performance overview, where to expand

NOTE: this controls what the DASHBOARD shows. It does not lock the other API endpoints by role.
"""
import json

from app.core.constants import parse_agent_code
from app.core.utils import fmt_time
from app.db.queries import latest_model_run
from app.ml.rebalance import plan_route


class Scope:
    """Everything a widget builder needs to know about this request."""

    def __init__(self, user, as_of_text, liquidity_time):
        self.user = user
        self.as_of_text = as_of_text
        self.liquidity_time = liquidity_time
        self.date_text = liquidity_time.strftime("%Y-%m-%d")
        self.district = user.district        # None means "all districts"


def widget(key, title, kind, data):
    return {"key": key, "title": title, "type": kind, "data": data}


def pick(source, *keys):
    """source['a']['b'] ... or None when any step is missing."""
    current = source
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


class DashboardService:
    def __init__(self, ctx, agent_intel, coverage):
        self.ctx = ctx                    # the Ctx object: pool, store, liquidity, anomaly, settings ...
        self.agent_intel = agent_intel    # may be None (B4/B7 add-on not installed)
        self.coverage = coverage          # may be None (C1 add-on not installed)

    # ============================================================ entry point
    async def build(self, user, as_of_text=None):
        liquidity_time = self.ctx.liquidity.parse_as_of(as_of_text)
        scope = Scope(user, as_of_text, liquidity_time)

        if user.role == "manager":
            builders = [
                ("liquidity_overview", self.manager_liquidity_overview),
                ("riskiest_agents", self.manager_riskiest_agents),
                ("delivery_route", self.manager_delivery_route),
                ("pending_alerts", self.manager_pending_alerts),
                ("retention", self.manager_retention),
                ("performance", self.performance_overview),
                ("coverage_gaps", self.coverage_gaps),
            ]
        elif user.role == "agent":
            builders = [
                ("my_status", self.agent_status),
                ("next_24_hours", self.agent_chart),
                ("why", self.agent_reasons),
                ("recent_activity", self.agent_recent_activity),
                ("my_performance", self.agent_performance),
            ]
        else:
            builders = [
                ("pending_alerts", self.analyst_alerts),
                ("review_activity", self.analyst_review_activity),
                ("model_quality", self.analyst_model_quality),
                ("performance", self.performance_overview),
                ("coverage_gaps", self.coverage_gaps),
            ]

        widgets = []
        warnings = []
        for key, builder in builders:
            try:
                built = await builder(scope)
                if built is not None:
                    widgets.append(built)
            except Exception as error:
                warnings.append(f"Widget '{key}' is unavailable: {error}")

        if user.role == "agent":
            scope_text = f"agent {user.agent_code}"
        elif user.district is not None:
            scope_text = f"district {user.district}"
        else:
            scope_text = "all districts"

        return {
            "user": {"username": user.username, "full_name": user.full_name, "role": user.role,
                     "district": user.district, "agent_code": user.agent_code},
            "scope": scope_text,
            "as_of": liquidity_time,
            "widgets": widgets,
            "warnings": warnings,
        }

    # ============================================================ MANAGER widgets
    async def manager_liquidity_overview(self, scope):
        table = await self.ctx.liquidity.risk_table(scope.liquidity_time, scope.district)
        counts = {}
        for level in ["HIGH", "MEDIUM", "LOW"]:
            counts[level] = int((table["risk_level"] == level).sum())
        needs_cash = table[table["risk_level"].isin(["HIGH", "MEDIUM"])]
        data = {
            "agents_in_scope": int(len(table)),
            "counts": counts,
            "total_cash_to_deliver_bdt": float(needs_cash["cash_topup_bdt"].sum()),
            "total_float_to_transfer_bdt": float(needs_cash["float_topup_bdt"].sum()),
            "details": "/risk",
        }
        return widget("liquidity_overview", "Cash and e-float risk (next 24 hours)", "stats", data)

    async def manager_riskiest_agents(self, scope):
        table = await self.ctx.liquidity.risk_table(scope.liquidity_time, scope.district)
        rows = []
        top = table.head(5)
        for row_number in range(len(top)):
            row = top.iloc[row_number]
            rows.append({
                "agent_code": row["agent_code"],
                "district": row["district"],
                "risk_level": row["risk_level"],
                "risk_side": row["risk_side"],
                "stockout_probability": round(float(row["stockout_prob"]), 2),
                "expected_stockout_time": fmt_time(row["p50_stockout_time"]),
                "cash_topup_bdt": float(row["cash_topup_bdt"]),
                "float_topup_bdt": float(row["float_topup_bdt"]),
                "details": f"/agents/{row['agent_code']}/forecast",
            })
        return widget("riskiest_agents", "Riskiest agents", "table", {"rows": rows})

    async def manager_delivery_route(self, scope):
        table = await self.ctx.liquidity.risk_table(scope.liquidity_time, scope.district)
        route = plan_route(table)
        next_stops = []
        for stop in route["stops"][0:3]:
            next_stops.append({"stop": stop["stop"], "agent_code": stop["agent_code"],
                               "cash_to_deliver_bdt": stop["cash_to_deliver_bdt"], "eta_min": stop["eta_min"]})
        data = {
            "stops": len(route["stops"]),
            "total_km": route["total_km"],
            "cash_to_carry_bdt": route["total_cash_bdt"],
            "digital_transfers": len(route["digital_transfers"]),
            "next_stops": next_stops,
            "details": "/rebalance",
        }
        return widget("delivery_route", "Cash delivery route", "route", data)

    async def alerts_in_scope(self, scope):
        alerts = await self.ctx.anomaly.alerts_for(scope.liquidity_time, status="pending")
        if scope.district is None:
            return alerts
        kept = []
        for alert in alerts:
            if alert["district"].lower() == scope.district.lower():
                kept.append(alert)
        return kept

    async def manager_pending_alerts(self, scope):
        alerts = await self.alerts_in_scope(scope)
        top = []
        for alert in alerts[0:3]:
            top.append({"alert_id": alert["alert_id"], "agent_code": alert["agent_code"], "severity": alert["severity"]})
        return widget("pending_alerts", "Suspicious activity waiting for review", "list",
                      {"count": len(alerts), "top": top, "details": "/alerts"})

    async def manager_retention(self, scope):
        intel = self.agent_intel
        if intel is None or intel.churn_model is None:
            return None
        week_index, table = intel.churn_table(scope.date_text)
        if scope.district is not None:
            table = table[table["district"].str.lower() == scope.district.lower()]
        at_risk = table[table["risk_level"].isin(["HIGH", "MEDIUM"])]
        rows = []
        for row_number in range(min(len(at_risk), 5)):
            row = at_risk.iloc[row_number]
            reason = ""
            if len(row["drivers"]) > 0:
                reason = row["drivers"][0]["text_en"]
            rows.append({"agent_code": row["agent_code"], "district": row["district"],
                         "churn_probability": float(row["churn_probability"]), "risk_level": row["risk_level"],
                         "top_reason": reason, "details": f"/intel/churn/agents/{row['agent_code']}"})
        data = {"high": int((at_risk["risk_level"] == "HIGH").sum()),
                "medium": int((at_risk["risk_level"] == "MEDIUM").sum()), "rows": rows}
        return widget("retention", "Agents at risk of leaving (next 4 weeks)", "table", data)

    # ============================================================ shared by manager and analyst
    async def performance_overview(self, scope):
        intel = self.agent_intel
        if intel is None:
            return None
        summary = intel.performance_summary(scope.date_text, scope.district)
        data = {"segments": summary["segments"], "clusters": summary["clusters"],
                "lost_volume_4w_at_service_gap_agents_bdt": summary["lost_volume_4w_at_service_gap_agents_bdt"],
                "details": "/intel/performance/summary"}
        return widget("performance", "Agent performance", "stats", data)

    async def coverage_gaps(self, scope):
        if self.coverage is None:
            return None
        summary = await self.coverage.summary(scope.date_text)
        gaps = await self.coverage.top_gaps(scope.date_text, None, 5)
        rows = []
        for gap in gaps:
            rows.append({"area": gap["nearest_town"], "gap_type": gap["gap_type"],
                         "opportunity_bdt_per_month": gap["opportunity_bdt_per_month"],
                         "recommendation": gap["recommendation"], "details": f"/coverage/cells/{gap['h3']}"})
        data = {"hexagons_by_gap_type": summary["hexagons_by_gap_type"], "rows": rows, "map": "/coverage/map",
                "note": summary["note"]}
        return widget("coverage_gaps", "Where to expand", "table", data)

    # ============================================================ AGENT widgets (only the agent's own data)
    async def own_forecast(self, scope):
        if scope.user.agent_code is None:
            raise ValueError("this account is not linked to an agent")
        agent_id = parse_agent_code(scope.user.agent_code)
        return await self.ctx.liquidity.agent_forecast(agent_id, scope.liquidity_time, include_history=True)

    async def agent_status(self, scope):
        forecast = await self.own_forecast(scope)
        data = {
            "agent_code": scope.user.agent_code,
            "cash_balance_bdt": forecast["current_balances"]["cash"],
            "e_float_balance_bdt": forecast["current_balances"]["e_float"],
            "risk_level": forecast["risk"]["level"],
            "risk_side": forecast["risk"]["side"],
            "stockout_probability": round(float(forecast["risk"]["stockout_probability"]), 2),
            "expected_stockout_time": fmt_time(forecast["risk"]["expected_stockout_time"]),
            "cash_topup_bdt": forecast["recommendation"]["cash_topup_bdt"],
            "float_topup_bdt": forecast["recommendation"]["float_topup_bdt"],
            "advice_en": forecast["recommendation"]["advice"]["en"],
            "advice_bn": forecast["recommendation"]["advice"]["bn"],
        }
        return widget("my_status", "My cash and e-float today", "stats", data)

    async def agent_chart(self, scope):
        forecast = await self.own_forecast(scope)
        points = []
        for hour in forecast["hourly"]:
            points.append({
                "time": hour["timestamp"],
                "cash_typical": hour["cash_balance_p50"],
                "cash_bad_day": hour["cash_balance_p90_worst"],
                "float_typical": hour["float_balance_p50"],
                "float_bad_day": hour["float_balance_p90_worst"],
            })
        return widget("next_24_hours", "Projected balances (below zero means you run out)", "chart", {"points": points})

    async def agent_reasons(self, scope):
        forecast = await self.own_forecast(scope)
        reasons = []
        for driver in forecast["drivers"]:
            reasons.append({"text_en": driver["text_en"], "text_bn": driver["text_bn"]})
        return widget("why", "Why", "list", {"reasons": reasons})

    async def agent_recent_activity(self, scope):
        forecast = await self.own_forecast(scope)
        days = {}
        order = []
        for hour in forecast["history"]:
            day = hour["timestamp"].strftime("%Y-%m-%d")
            if day not in days:
                days[day] = {"day": day, "cash_out_bdt": 0.0, "cash_in_bdt": 0.0, "stockout_hours": 0}
                order.append(day)
            days[day]["cash_out_bdt"] = days[day]["cash_out_bdt"] + float(hour["cash_out_amt"])
            days[day]["cash_in_bdt"] = days[day]["cash_in_bdt"] + float(hour["cash_in_amt"])
            if bool(hour["stockout"]):
                days[day]["stockout_hours"] = days[day]["stockout_hours"] + 1
        rows = []
        for day in order:
            rows.append(days[day])
        return widget("recent_activity", "Last 3 days", "table", {"rows": rows})

    async def agent_performance(self, scope):
        intel = self.agent_intel
        if intel is None or scope.user.agent_code is None:
            return None
        detail = intel.performance_agent(parse_agent_code(scope.user.agent_code), scope.date_text)
        if detail is None:
            return None
        data = {"segment": detail["segment"], "performance_score": detail["performance_score"],
                "volume_percentile_among_similar_agents": round(float(detail["volume_percentile"]), 0)}
        return widget("my_performance", "How I compare with similar agents", "stats", data)

    # ============================================================ ANALYST widgets
    async def analyst_alerts(self, scope):
        alerts = await self.ctx.anomaly.alerts_for(scope.liquidity_time, status="pending")
        rows = []
        for alert in alerts[0:10]:
            signals = []
            for reason in alert["reasons"]:
                signals.append(reason["label"] + ": " + reason["detail"])
            rows.append({"alert_id": alert["alert_id"], "agent_code": alert["agent_code"], "district": alert["district"],
                         "severity": alert["severity"], "signals": signals,
                         "details": f"/alerts/{alert['alert_id']}/narrative"})
        return widget("pending_alerts", "Alerts to review", "table", {"count": len(alerts), "rows": rows})

    async def analyst_review_activity(self, scope):
        pool = self.ctx.pool
        status_rows = await pool.fetch("SELECT status, count(*) AS total FROM alert_reviews GROUP BY status")
        totals = {"confirmed": 0, "dismissed": 0}
        for record in status_rows:
            totals[record["status"]] = int(record["total"])
        recent_rows = await pool.fetch(
            "SELECT alert_id, status, reviewer, reviewed_at FROM alert_reviews ORDER BY reviewed_at DESC LIMIT 5")
        recent = []
        for record in recent_rows:
            recent.append({"alert_id": record["alert_id"], "status": record["status"], "reviewer": record["reviewer"],
                           "reviewed_at": record["reviewed_at"].isoformat()})
        return widget("review_activity", "Review activity", "stats", {"totals": totals, "recent": recent})

    async def load_metrics(self):
        run = await latest_model_run(self.ctx.pool)
        if run is not None:
            return run["metrics"]
        path = self.ctx.settings.artifact_dir / "metrics.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    async def analyst_model_quality(self, scope):
        metrics = await self.load_metrics()
        if metrics is None:
            return None
        data = {
            "forecast_error_reduction_vs_baseline_pct": pick(metrics, "hourly_forecast", "mae_improvement_pct"),
            "daily_error_reduction_vs_baseline_pct": pick(metrics, "hourly_forecast", "daily_wape_improvement_pct"),
            "p90_cash_coverage": pick(metrics, "peak_drain_p90", "coverage_cash_ai"),
            "p90_float_coverage": pick(metrics, "peak_drain_p90", "coverage_float_ai"),
            "stockout_hours_reduction_vs_habitual_pct": pick(metrics, "policy_simulation", "summary",
                                                             "stockout_hours_reduction_vs_habitual_matched_pct"),
            "anomaly_auc": pick(metrics, "anomaly", "roc_auc_agent_day"),
            "anomaly_precision": pick(metrics, "anomaly", "precision_at_threshold"),
            "anomaly_recall": pick(metrics, "anomaly", "recall_at_threshold"),
            "details": "/metrics",
            "note": "Measured on synthetic data.",
        }
        intel = self.agent_intel
        if intel is not None and intel.churn_model is not None:
            data["churn_auc"] = intel.churn_metrics.get("auc_model")
        return widget("model_quality", "Model quality", "stats", data)
