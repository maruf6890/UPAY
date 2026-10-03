"""Vectorised agent liquidity simulator (shared by the data generator and the policy evaluation).

Each agent holds two balances:
  cash  - physical cash in the drawer
  flt   - e-money float in the agent wallet
Cash-out (customer withdraws): cash falls, float rises.  Cash-in (customer deposits): cash rises, float falls.
"""
from __future__ import annotations

import numpy as np


def morning_rebalance(cash, flt, t_cash, t_flt, active):
    """Reset the agent to its planned inventory (t_cash, t_flt): first swap surplus of one side into the other
    (bank / e-float conversion), then inject external money for any remaining deficit and sweep any remaining
    excess back to the bank. Total liquidity committed therefore equals the target. Returns (cash, flt, injected)."""
    active = np.asarray(active, dtype=float)
    d_cash = np.maximum(t_cash - cash, 0.0)
    s_flt = np.maximum(flt - t_flt, 0.0)
    x = np.minimum(d_cash, s_flt) * active
    cash = cash + x
    flt = flt - x

    d_flt = np.maximum(t_flt - flt, 0.0)
    s_cash = np.maximum(cash - t_cash, 0.0)
    y = np.minimum(d_flt, s_cash) * active
    flt = flt + y
    cash = cash - y

    inj_c = np.maximum(t_cash - cash, 0.0) * active
    inj_f = np.maximum(t_flt - flt, 0.0) * active
    cash = np.where(active > 0, t_cash, cash)      # after injection / sweep both balances equal the target
    flt = np.where(active > 0, t_flt, flt)
    return cash, flt, inj_c + inj_f


MIN_SHORT_BDT = 2000.0   # STOCKOUT DEFINITION: an hour with > ৳2,000 of unserved demand (~ at least one failed typical transaction)


def simulate(out, inn, t_cash, t_flt, cash0, flt0, active=None, emergency_prob=0.0, rng=None, min_short=MIN_SHORT_BDT):
    """out/inn: demand cubes (A, D, H). t_cash/t_flt: morning targets (A, D).
    Returns dict of cubes: cash_end, flt_end, stockout (bool), unserved (BDT) and per-day injected / start liquidity."""
    A, D, H = out.shape
    cash = np.asarray(cash0, dtype=float).copy()
    flt = np.asarray(flt0, dtype=float).copy()
    cash_end = np.zeros((A, D, H), dtype=np.float32)
    flt_end = np.zeros((A, D, H), dtype=np.float32)
    stockout = np.zeros((A, D, H), dtype=bool)
    unserved = np.zeros((A, D, H), dtype=np.float32)
    injected = np.zeros((A, D))
    start_liq = np.zeros((A, D))

    for d in range(D):
        act = np.ones(A) if active is None else active[:, d]
        cash, flt, inj = morning_rebalance(cash, flt, t_cash[:, d], t_flt[:, d], act)
        injected[:, d] = inj
        start_liq[:, d] = cash + flt
        for h in range(H):
            o = out[:, d, h]
            i = inn[:, d, h]
            o_s = np.minimum(o, cash)      # cannot pay out more cash than the drawer holds
            i_s = np.minimum(i, flt)       # cannot accept more cash-in than e-float available
            short = (o - o_s) + (i - i_s)
            so = short > min_short
            cash = cash - o_s + i_s
            flt = flt + o_s - i_s
            if emergency_prob > 0 and rng is not None:
                em = so & (rng.random(A) < emergency_prob)
                cash, flt, inj2 = morning_rebalance(cash, flt, t_cash[:, d], t_flt[:, d], em)
                injected[:, d] += inj2
            cash_end[:, d, h] = cash
            flt_end[:, d, h] = flt
            stockout[:, d, h] = so
            unserved[:, d, h] = short
    return dict(cash_end=cash_end, flt_end=flt_end, stockout=stockout, unserved=unserved,
                injected=injected, start_liq=start_liq)
