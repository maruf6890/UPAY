"""Greedy rebalancing plan for a DSO (distributor sales officer): pick the agents that most need CASH delivered,
within the van's cash capacity, then order the visits by nearest-neighbour from the depot.
Float shortfalls are digital transfers - no visit needed."""
from __future__ import annotations

import numpy as np
import pandas as pd


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return float(2 * r * np.arcsin(np.sqrt(a)))


def plan_route(risk: pd.DataFrame, van_capacity_bdt: float = 5_000_000, max_stops: int = 12,
               depot: tuple[float, float] | None = None, speed_kmph: float = 30.0, minutes_per_stop: int = 10) -> dict:
    cand = risk[(risk.cash_topup_bdt > 0) & (risk.risk_level.isin(["HIGH", "MEDIUM"]))].copy()
    float_only = risk[(risk.float_topup_bdt > 0) & (risk.risk_level.isin(["HIGH", "MEDIUM"]))]
    digital = float_only[["agent_code", "float_topup_bdt"]].to_dict("records")
    if cand.empty:
        return dict(stops=[], total_km=0.0, total_cash_bdt=0.0, digital_transfers=digital, depot=None, unserved=[])
    cand["priority"] = cand.stockout_prob * cand.cash_topup_bdt
    cand = cand.sort_values("priority", ascending=False)
    chosen, used = [], 0.0
    for _, r in cand.iterrows():                     # greedy knapsack by priority
        if len(chosen) >= max_stops:
            break
        if len(chosen) == 0:
            nothing_served = cand[["agent_code", "cash_topup_bdt"]].head(10).to_dict("records")
            return dict(stops=[], total_km=0.0, total_cash_bdt=0.0, digital_transfers=digital, depot=None, unserved=nothing_served)
        if used + r.cash_topup_bdt <= van_capacity_bdt:
            chosen.append(r)
            used += r.cash_topup_bdt
    chosen_ids = {r.agent_code for r in chosen}
    unserved = cand[~cand.agent_code.isin(chosen_ids)][["agent_code", "cash_topup_bdt"]].head(10).to_dict("records")
    pts = pd.DataFrame(chosen)
    dep = depot or (float(pts.lat.mean()), float(pts.lon.mean()))
    cur, left, order, total_km, clock = dep, list(range(len(pts))), [], 0.0, 0.0
    while left:                                      # nearest-neighbour ordering
        j = min(left, key=lambda i: haversine_km(cur[0], cur[1], pts.iloc[i].lat, pts.iloc[i].lon))
        r = pts.iloc[j]
        leg = haversine_km(cur[0], cur[1], r.lat, r.lon)
        total_km += leg
        clock += leg / speed_kmph * 60 + minutes_per_stop
        order.append(dict(stop=len(order) + 1, agent_code=r.agent_code, district=r.district,
                          lat=round(float(r.lat), 4), lon=round(float(r.lon), 4), leg_km=round(leg, 1),
                          eta_min=int(round(clock)), cash_to_deliver_bdt=float(r.cash_topup_bdt),
                          stockout_prob=round(float(r.stockout_prob), 2), risk_level=r.risk_level,
                          first_risk_time=r.get("p90_stockout_time")))
        cur = (r.lat, r.lon)
        left.remove(j)
    return dict(stops=order, total_km=round(total_km, 1), total_cash_bdt=float(used),
                digital_transfers=digital, depot={"lat": round(dep[0], 4), "lon": round(dep[1], 4)}, unserved=unserved)
