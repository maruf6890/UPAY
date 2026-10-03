"""Plain-language explanations from LightGBM's native SHAP values (pred_contrib=True) - no extra dependency.
SHAP values of the P50 model are summed over the hours up to the peak-risk hour, grouped into business themes."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.features import FEATURES

THEMES = {
    "eid": (["days_to_eid", "days_since_eid", "is_eid_holiday"], "Eid effect", "ঈদের প্রভাব"),
    "salary": (["is_salary_week"], "Salary week", "বেতনের সপ্তাহ"),
    "remittance": (["is_remit_window"], "Remittance window", "রেমিট্যান্স আসার সময়"),
    "market": (["is_haat_day"], "Market (haat) day", "হাটের দিন"),
    "ramadan": (["is_ramadan"], "Ramadan pattern", "রমজানের ধরন"),
    "weather": (["rain_mm", "rain_3d"], "Rain / weather", "বৃষ্টি ও আবহাওয়া"),
    "weekday": (["dow", "is_friday", "dom"], "Day-of-week / date pattern", "সপ্তাহের দিন ও তারিখ"),
    "time": (["hour"], "Time-of-day pattern", "দিনের সময়"),
    "recent": (["net_lag_1d", "net_lag_2d", "net_lag_7d", "out_lag_1d", "in_lag_1d", "net_mean_7d",
                "net_std_7d", "gross_mean_7d", "net_day_mean_14d", "gross_day_mean_14d"],
               "Recent transaction trend", "সাম্প্রতিক লেনদেনের ধারা"),
    "profile": (["arch_code", "area_code", "out_share"], "Agent type & area", "এজেন্টের ধরন ও এলাকা"),
}


def explain_window(booster, X: pd.DataFrame, scale: float, upto: int, side: str, top: int = 3) -> list[dict]:
    """X: the feature rows (<=16) of ONE agent's window. upto: index of the peak-risk hour (inclusive).
    side 'cash' => positive contribution = more cash drain; 'float' => sign flipped."""
    contrib = booster.predict(X[FEATURES], pred_contrib=True, num_iteration=booster.best_iteration)[:, :-1]
    contrib = contrib[: upto + 1].sum(axis=0) * scale          # BDT over the window up to the peak hour
    sign = 1.0 if side == "cash" else -1.0
    by = dict(zip(FEATURES, contrib * sign))
    rows = []
    for key, (cols, en, bn) in THEMES.items():
        v = float(sum(by[c] for c in cols))
        rows.append(dict(theme=key, label_en=en, label_bn=bn, impact_bdt=round(v, 0)))
    rows.sort(key=lambda r: -abs(r["impact_bdt"]))
    word = "cash" if side == "cash" else "float"
    for r in rows:
        up = r["impact_bdt"] > 0
        r["direction"] = "increases" if up else "reduces"
        r["text_en"] = f"{r['label_en']} {r['direction']} expected {word} drain by about ৳{abs(r['impact_bdt']):,.0f}"
        r["text_bn"] = f"{r['label_bn']}: প্রত্যাশিত {'ক্যাশ' if side == 'cash' else 'ই-ফ্লোট'} চাহিদা ≈ ৳{abs(r['impact_bdt']):,.0f} {'বেশি' if up else 'কম'}"
    return rows[:top]
