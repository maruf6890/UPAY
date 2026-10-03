"""Bangladesh calendar features. Dates are APPROXIMATE (moon-sighting dependent) - fine for synthetic data."""
from __future__ import annotations

import numpy as np
import pandas as pd

RAMADAN = [("2025-03-01", "2025-03-30"), ("2026-02-19", "2026-03-19"), ("2027-02-08", "2027-03-09")]
EID_DATES = ["2025-03-31", "2025-06-07", "2026-03-21", "2026-05-28", "2027-03-10", "2027-05-17"]

CAL_COLUMNS = [
    "dow", "dom", "is_friday", "is_salary_week", "is_remit_window", "is_ramadan",
    "is_eid_holiday", "days_to_eid", "days_since_eid",
]


def build_calendar(dates) -> pd.DataFrame:
    d = pd.DatetimeIndex(pd.to_datetime(pd.Series(dates).unique())).normalize().sort_values()
    eids = pd.to_datetime(EID_DATES).values
    diff = ((eids[None, :] - d.values[:, None]).astype("timedelta64[D]")).astype(int)  # eid - date

    big = 999
    days_to = np.where(diff >= 0, diff, big).min(axis=1)
    days_since = np.where(diff < 0, -diff, big).min(axis=1)

    ram = np.zeros(len(d), dtype=bool)
    for a, b in RAMADAN:
        ram |= (d >= pd.Timestamp(a)) & (d <= pd.Timestamp(b))

    cal = pd.DataFrame({"date": d})
    cal["dow"] = d.dayofweek.astype("int8")                      # Mon=0 ... Fri=4, Sat=5
    cal["dom"] = d.day.astype("int8")
    cal["is_friday"] = (cal["dow"] == 4).astype("int8")
    cal["is_salary_week"] = (cal["dom"] <= 7).astype("int8")      # salary / garment-wage window
    cal["is_remit_window"] = cal["dom"].between(8, 12).astype("int8")
    cal["is_ramadan"] = ram.astype("int8")
    cal["is_eid_holiday"] = ((days_to <= 1) | (days_since <= 2)).astype("int8")
    cal["days_to_eid"] = np.minimum(days_to, 30).astype("int16")
    cal["days_since_eid"] = np.minimum(days_since, 30).astype("int16")
    return cal
