"""Turn hourly quantile forecasts into liquidity decisions (kept separate from the ML model = business-rules layer).

Net flow  n_t = cash_out_t - cash_in_t.  cash balance falls by n_t, e-float rises by n_t.
  cash drain over hours 1..h  = cumsum(n)          -> risk when it gets large and positive
  float drain over hours 1..h = -cumsum(n)         -> risk when it gets large and negative
Per-hour quantiles cannot simply be summed (that would be far too conservative), so the cumulative P90 band is built as
    cum_P50 + k * z90 * sqrt(cumsum(sigma_h^2)),   sigma_h from the hourly (P90-P50) or (P50-P10) spread,
where k is a calibration factor fitted on a validation period so the daily PEAK-drain P90 really covers 90% of outcomes.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

from app.core.constants import Z90


def cumulative_bands(q10, q50, q90, k_cash: float = 1.0, k_flt: float = 1.0):
    """Arrays (..., H). Returns dict with cumulative P50 and P90 drain paths for cash and float."""
    q10, q50, q90 = np.sort(np.stack([q10, q50, q90]), axis=0)
    s_up = np.maximum(q90 - q50, 0) / Z90
    s_dn = np.maximum(q50 - q10, 0) / Z90
    cum_mu = np.cumsum(q50, axis=-1)
    sd_up = np.sqrt(np.cumsum(s_up ** 2, axis=-1))
    sd_dn = np.sqrt(np.cumsum(s_dn ** 2, axis=-1))
    return dict(
        cum_mu=cum_mu, sd_up=sd_up, sd_dn=sd_dn,
        cash_p90=cum_mu + k_cash * Z90 * sd_up,       # cumulative cash drain (upper band)
        flt_p90=-cum_mu + k_flt * Z90 * sd_dn,        # cumulative float drain (upper band)
    )


def peak_need(path: np.ndarray) -> np.ndarray:
    """Liquidity needed at the start of the window to survive the whole window."""
    return np.maximum(path.max(axis=-1), 0.0)


def calibrate_k(q10, q50, q90, actual_net, side: str, target: float = 0.90) -> float:
    """Smallest k (grid) such that the P90 peak-drain forecast covers `target` of realised daily peaks.
    Arrays are (A, D, H)."""
    act_cum = np.cumsum(actual_net, axis=-1)
    act_peak = np.maximum((act_cum if side == "cash" else -act_cum).max(axis=-1), 0.0)
    for k in np.arange(0.5, 4.01, 0.05):
        b = cumulative_bands(q10, q50, q90, k_cash=k, k_flt=k)
        pred = peak_need(b["cash_p90"] if side == "cash" else b["flt_p90"])
        if (act_peak <= pred + 1e-6).mean() >= target:
            return float(round(k, 2))
    return 4.0


def stockout_probability(avail: np.ndarray, cum_mu: np.ndarray, sd: np.ndarray, k: float,
                         side: str, reserve: float) -> np.ndarray:
    """Approximate P(stockout at some point in the window) = max over hours of P(drain_h > avail - reserve).
    avail (...,) ; cum_mu/sd (..., H)."""
    mu = cum_mu if side == "cash" else -cum_mu
    z = (avail[..., None] - reserve - mu) / np.maximum(k * sd, 1e-6)
    return (1.0 - norm.cdf(z)).max(axis=-1)


def risk_level(p: float) -> str:
    return "HIGH" if p >= 0.5 else "MEDIUM" if p >= 0.2 else "LOW"
