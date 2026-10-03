"""Liquidity forecasting service: builds the feature window, runs the quantile models, applies the business rules."""
from __future__ import annotations

import asyncio
from collections import OrderedDict

import numpy as np
import pandas as pd

from app.core.config import Settings
from app.core.constants import N_OPEN, agent_code
from app.core.utils import fmt_time
from app.ml.explain import explain_window
from app.ml.features import build_feature_frame
from app.ml.forecasting import baseline_quantiles, load_artifacts, predict_quantiles
from app.ml.liquidity import cumulative_bands, peak_need, risk_level, stockout_probability
from app.services.store import DataStore


def _first_breach(path: np.ndarray, avail: np.ndarray, reserve: float) -> np.ndarray:
    breach = (avail[:, None] - path) < reserve
    return np.where(breach.any(axis=1), breach.argmax(axis=1), -1)


class LiquidityService:
    def __init__(self, store: DataStore, s: Settings):
        self.store, self.s = store, s
        self.models, self.scale, self.calib = load_artifacts(s)
        self._cache: OrderedDict[pd.Timestamp, dict] = OrderedDict()
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ helpers
    def default_as_of(self) -> pd.Timestamp:
        return pd.Timestamp(self.s.demo_as_of).floor("h")

    def parse_as_of(self, as_of: str | pd.Timestamp | None) -> pd.Timestamp:
        ts = self.default_as_of() if as_of is None else pd.Timestamp(as_of).floor("h")
        lo = self.store.data_start.normalize() + pd.Timedelta(days=10)
        hi = self.store.data_end.normalize() + pd.Timedelta(hours=23)
        if not (lo <= ts <= hi):
            raise ValueError(f"as_of must be between {lo} and {hi}")
        return ts

    # ------------------------------------------------------------------ core
    async def assess(self, as_of=None) -> dict:
        """Async: reads the 30-day window from PostgreSQL, then runs the CPU-heavy model in a worker thread."""
        ts = self.parse_as_of(as_of)
        async with self._lock:
            if ts in self._cache:
                self._cache.move_to_end(ts)
                return self._cache[ts]
            d0 = ts.normalize()
            h = await self.store.hourly_window(d0 - pd.Timedelta(days=30), d0 + pd.Timedelta(days=2))   # +2d: realised outcome for the demo
            res = await asyncio.to_thread(self._compute, ts, h)
            self._cache[ts] = res
            while len(self._cache) > 6:
                self._cache.popitem(last=False)
            return res

    def _compute(self, ts: pd.Timestamp, h: pd.DataFrame) -> dict:
        st, c, reserve = self.store, self.calib, self.s.reserve_bdt
        frame = build_feature_frame(h, st.agents, st.weather, self.scale, pad_days=2)
        t = frame[(frame.timestamp >= ts) & (frame.timestamp < ts + pd.Timedelta(hours=24))].reset_index(drop=True)
        A = len(st.agent_ids)
        assert len(t) == A * N_OPEN, "window must contain 16 open hours per agent"
        q = predict_quantiles(self.models, t)
        b = baseline_quantiles(t)
        cube = lambda df, col: df[col].to_numpy().reshape(A, N_OPEN)
        qs = [cube(q, k) for k in ("q10", "q50", "q90")]
        bs = [cube(b, k) for k in ("q10", "q50", "q90")]
        times = t.timestamp.to_numpy().reshape(A, N_OPEN)

        prev = h[h.timestamp < ts]
        bal = prev.sort_values(["agent_id", "timestamp"]).groupby("agent_id").tail(1).set_index("agent_id").loc[st.agent_ids]
        cash0, flt0 = bal.cash_balance.to_numpy(float), bal.float_balance.to_numpy(float)

        bands = cumulative_bands(*qs, c["k_cash"], c["k_flt"])
        bbands = cumulative_bands(*bs, c["k_cash_base"], c["k_flt_base"])
        need_c, need_f = peak_need(bands["cash_p90"]), peak_need(bands["flt_p90"])
        bneed_c, bneed_f = peak_need(bbands["cash_p90"]), peak_need(bbands["flt_p90"])
        p_c = stockout_probability(cash0, bands["cum_mu"], bands["sd_up"], c["k_cash"], "cash", reserve)
        p_f = stockout_probability(flt0, bands["cum_mu"], bands["sd_dn"], c["k_flt"], "float", reserve)
        side = np.where(p_c >= p_f, "cash", "float")
        prob = np.maximum(p_c, p_f)

        i90 = np.where(side == "cash", _first_breach(bands["cash_p90"], cash0, reserve), _first_breach(bands["flt_p90"], flt0, reserve))
        i50 = np.where(side == "cash", _first_breach(bands["cum_mu"], cash0, reserve), _first_breach(-bands["cum_mu"], flt0, reserve))
        pick = lambda idx: [pd.Timestamp(times[a, i]) if i >= 0 else pd.NaT for a, i in enumerate(idx)]

        ag = st.agents
        risk = pd.DataFrame({
            "agent_id": ag.agent_id.values, "agent_code": ag.agent_code.values, "district": ag.district.values,
            "division": ag.division.values, "archetype": ag.archetype.values, "area_type": ag.area_type.values,
            "lat": ag.lat.values, "lon": ag.lon.values,
            "cash_balance": cash0, "float_balance": flt0, "risk_side": side, "stockout_prob": prob,
            "risk_level": [risk_level(p) for p in prob],
            "need_cash_p90": need_c, "need_float_p90": need_f,
            "cash_topup_bdt": np.maximum(need_c + reserve - cash0, 0).round(-2),
            "float_topup_bdt": np.maximum(need_f + reserve - flt0, 0).round(-2),
            "p50_stockout_time": pick(i50), "p90_stockout_time": pick(i90),
            "baseline_cash_topup_bdt": np.maximum(bneed_c + reserve - cash0, 0).round(-2),
            "baseline_float_topup_bdt": np.maximum(bneed_f + reserve - flt0, 0).round(-2),
        })
        # realised outcome (only exists when as_of lies inside the synthetic history)
        a = h[(h.timestamp >= ts) & (h.timestamp < ts + pd.Timedelta(hours=24))]
        actual = None
        if len(a) == A * N_OPEN:
            a = a.sort_values(["agent_id", "timestamp"])
            actual = (a.cash_out_amt.to_numpy(float) - a.cash_in_amt.to_numpy(float)).reshape(A, N_OPEN)
            cum = np.cumsum(actual, axis=1)
            risk["actual_peak_cash_drain"] = np.maximum(cum.max(1), 0)
            risk["actual_peak_float_drain"] = np.maximum((-cum).max(1), 0)
            risk["would_have_stocked_out"] = (risk.actual_peak_cash_drain + reserve > risk.cash_balance) | (risk.actual_peak_float_drain + reserve > risk.float_balance)
        res = dict(as_of=ts, frame=t, q=qs, b=bs, bands=bands, bbands=bbands, cash0=cash0, flt0=flt0,
                   times=times, risk=risk, actual=actual)
        return res

    # ------------------------------------------------------------------ views
    async def risk_table(self, as_of=None, district: str | None = None) -> pd.DataFrame:
        r = (await self.assess(as_of))["risk"]
        if district:
            r = r[r.district.str.lower() == district.lower()]
        return r.sort_values("stockout_prob", ascending=False)

    def advice(self, row) -> dict:
        reserve = self.s.reserve_bdt
        if row["risk_level"] == "LOW":
            return dict(en="No action needed: balances should cover the next 24 hours.",
                        bn="কোনো পদক্ষেপের প্রয়োজন নেই: আগামী ২৪ ঘণ্টার জন্য ব্যালেন্স যথেষ্ট।")
        side = row["risk_side"]
        amt = row["cash_topup_bdt"] if side == "cash" else row["float_topup_bdt"]
        when = fmt_time(row["p50_stockout_time"] if pd.notna(row["p50_stockout_time"]) else row["p90_stockout_time"])
        noun_en, noun_bn = ("cash", "ক্যাশ") if side == "cash" else ("e-float", "ই-ফ্লোট")
        return dict(
            en=f"Risk of running out of {noun_en} (around {when}). Add about ৳{amt:,.0f} {noun_en} before the day starts.",
            bn=f"{noun_bn} শেষ হওয়ার ঝুঁকি আছে (প্রায় {when})। দিন শুরুর আগে প্রায় ৳{amt:,.0f} {noun_bn} বাড়ান।")

    async def agent_forecast(self, agent_id: int, as_of=None, include_history: bool = True) -> dict:
        res = await self.assess(as_of)
        i = int(np.where(self.store.agent_ids == agent_id)[0][0])
        row = res["risk"].iloc[i]
        qs, bs, bands, bb = res["q"], res["b"], res["bands"], res["bbands"]
        cash0, flt0 = res["cash0"][i], res["flt0"][i]
        side = row["risk_side"]
        peak_path = bands["cash_p90"][i] if side == "cash" else bands["flt_p90"][i]
        peak_idx = int(np.argmax(peak_path))
        rows = res["frame"].iloc[i * N_OPEN:(i + 1) * N_OPEN]
        expl = explain_window(self.models["q50"], rows, float(rows.scale.iloc[0]), peak_idx, side)
        hours = []
        for h in range(N_OPEN):
            hours.append(dict(
                timestamp=pd.Timestamp(res["times"][i, h]), net_q10=qs[0][i, h], net_q50=qs[1][i, h], net_q90=qs[2][i, h],
                baseline_net_q50=bs[1][i, h],
                cash_balance_p50=cash0 - bands["cum_mu"][i, h], cash_balance_p90_worst=cash0 - bands["cash_p90"][i, h],
                float_balance_p50=flt0 + bands["cum_mu"][i, h], float_balance_p90_worst=flt0 - bands["flt_p90"][i, h],
                actual_net=None if res["actual"] is None else res["actual"][i, h],
            ))
        history = []
        if include_history:
            hist = await self.store.hourly_window(res["as_of"] - pd.Timedelta(days=3), res["as_of"], agent_id)
            history = hist[["timestamp", "cash_out_amt", "cash_in_amt", "cash_balance", "float_balance", "stockout"]].to_dict("records")
        reserve = self.s.reserve_bdt
        return dict(
            agent=self.store.agent_row(agent_id)[["agent_code", "district", "division", "archetype", "area_type", "lat", "lon"]].to_dict(),
            as_of=res["as_of"], horizon_hours=24, reserve_bdt=reserve,
            current_balances=dict(cash=cash0, e_float=flt0),
            risk=dict(level=row["risk_level"], side=side, stockout_probability=row["stockout_prob"],
                      expected_stockout_time=row["p50_stockout_time"], possible_stockout_time_p90=row["p90_stockout_time"]),
            recommendation=dict(cash_topup_bdt=row["cash_topup_bdt"], float_topup_bdt=row["float_topup_bdt"],
                                need_cash_p90=row["need_cash_p90"], need_float_p90=row["need_float_p90"], advice=self.advice(row)),
            baseline_comparison=dict(
                method="7-day moving average of the same hour",
                baseline_cash_topup_bdt=row["baseline_cash_topup_bdt"], baseline_float_topup_bdt=row["baseline_float_topup_bdt"],
                actual_peak_cash_drain=row.get("actual_peak_cash_drain"), actual_peak_float_drain=row.get("actual_peak_float_drain")),
            drivers=expl, hourly=hours,
            history=history,
            notes="Probabilities are model estimates. Recommendations are advisory; the agent / DSO decides.")
