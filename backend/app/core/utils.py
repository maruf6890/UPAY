from __future__ import annotations

import math
from datetime import date, datetime

import numpy as np
import pandas as pd


def clean(o):
    """Recursively convert numpy / pandas objects into JSON-safe python types (NaN -> None)."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, pd.DataFrame):
        return clean(o.to_dict("records"))
    if isinstance(o, (pd.Timestamp, datetime, date)):
        return o.isoformat()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if o is pd.NaT:
        return None
    return o


def fmt_time(ts) -> str | None:
    if ts is None or (isinstance(ts, float) and math.isnan(ts)) or ts is pd.NaT:
        return None
    return pd.Timestamp(ts).strftime("%a %I:%M %p")
