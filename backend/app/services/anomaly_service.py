"""Anomaly alerts for the analyst queue (recommendations only - a human confirms or dismisses)."""
from __future__ import annotations

import pandas as pd

from app.core.config import Settings
from app.core.constants import agent_code
from app.ml import anomaly as anom
from app.services.store import AlertStore, DataStore


class AnomalyService:
    def __init__(self, store: DataStore, s: Settings, alerts: AlertStore):
        self.store, self.alerts = store, alerts
        self.model, self.thr = anom.load(s)
        self.scored = anom.score(self.model, anom.build_features(store.daily, store.agents))
        self.scored["agent_code"] = self.scored.agent_id.map(agent_code)

    async def alerts_for(self, as_of: pd.Timestamp, lookback_days: int = 3, status: str | None = None, limit: int = 30) -> list[dict]:
        last_day = as_of.normalize() - pd.Timedelta(days=1)          # last COMPLETE day before as_of
        w = self.scored[(self.scored.date <= last_day) & (self.scored.date > last_day - pd.Timedelta(days=lookback_days))]
        w = w[w.alert_score >= self.thr["medium"]].sort_values("date").groupby("agent_id").tail(1)
        out = []
        w = w.sort_values("alert_score", ascending=False)
        reviews = await self.alerts.get_many([f"{r.agent_code}_{r.date:%Y-%m-%d}" for r in w.itertuples()])
        for _, r in w.iterrows():
            aid = f"{r.agent_code}_{r.date:%Y-%m-%d}"
            rev = reviews.get(aid) or {"status": "pending"}
            if status and rev["status"] != status:
                continue
            ag = self.store.agent_row(int(r.agent_id))
            out.append(dict(alert_id=aid, agent_code=r.agent_code, district=ag.district, archetype=ag.archetype,
                            date=f"{r.date:%Y-%m-%d}", anomaly_score=round(float(r.alert_score), 3),
                            severity="HIGH" if r.alert_score >= self.thr["high"] else "MEDIUM",
                            reasons=anom.reasons(r), review=rev,
                            next_step="Analyst review: check recent transactions and counterparties; no automatic action is taken."))
        return out[:limit]

    async def get_alert(self, alert_id: str) -> dict:
        code, day = alert_id.split("_")
        r = self.scored[(self.scored.agent_code == code) & (self.scored.date == pd.Timestamp(day))]
        if r.empty:
            raise KeyError(alert_id)
        r = r.iloc[0]
        ag = self.store.agent_row(int(r.agent_id))
        rev = await self.alerts.get(alert_id) or {"status": "pending"}
        return dict(alert_id=alert_id, agent_code=code, district=ag.district, archetype=ag.archetype, date=f"{r.date:%Y-%m-%d}",
                    anomaly_score=round(float(r.alert_score), 3), reasons=anom.reasons(r, top=4), review=rev)

    def score_history(self, agent_id: int, days: int = 30, as_of: pd.Timestamp | None = None) -> list[dict]:
        d = self.scored[self.scored.agent_id == agent_id]
        if as_of is not None:
            d = d[d.date < as_of.normalize()]
        return d.tail(days)[["date", "alert_score"]].to_dict("records")
