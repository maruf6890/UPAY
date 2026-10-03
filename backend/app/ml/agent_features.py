"""One feature table for both B4 (performance) and B7 (churn).

One row = one agent in one week. Every value uses only that week and EARLIER weeks,
so the table never looks into the future.

Baseline = the agent's own median of its first 8 weeks. Ratios compare the agent with itself.
"""
import numpy as np
import pandas as pd

BASELINE_WEEKS = 8

# columns the churn model is allowed to see
CHURN_FEATURES = [
    "txn_ratio_1w_vs_peers",   # last week's transactions vs own baseline, divided by what SIMILAR agents did
    "txn_ratio_4w_vs_peers",   # same for the 4-week average
    "txn_trend_vs_peers",      # 2-week trend vs the trend of similar agents
    "volume_ratio_4w",     # 4-week average volume / own baseline
    "ticket_ratio_4w",     # 4-week average ticket size / own baseline
    "active_days_1w",      # days with at least one transaction last week
    "active_days_4w",      # same, 4-week average
    "stockout_hours_4w",   # hours without cash/float in the last 4 weeks
    "stockout_rate_4w",    # the same as a share of open hours
    "txn_volatility_4w",   # how unstable the last 4 weeks were
    "archetype_code",
    "area_code",
]

ARCHETYPE_CODES = {"urban_market": 0, "garment_zone": 1, "rural_remittance": 2, "transit_hub": 3}
AREA_CODES = {"urban": 0, "semi_urban": 1, "rural": 2}


def build_feature_table(weekly, agents):
    """weekly: agent_weekly table. agents: agents table (needs archetype and area_type)."""
    agent_info = agents[["agent_id", "archetype", "area_type"]]
    pieces = []

    for agent_id, group in weekly.groupby("agent_id"):
        group = group.sort_values("week_index").reset_index(drop=True)

        # the agent's own normal level, from its first weeks
        first_weeks = group.iloc[0:BASELINE_WEEKS]
        baseline_txn = float(first_weeks["txn_count"].median())
        baseline_volume = float(first_weeks["volume_bdt"].median())
        baseline_ticket = float(first_weeks["avg_ticket"].median())
        if baseline_txn <= 0:
            continue

        transactions = group["txn_count"]
        volume = group["volume_bdt"]
        ticket = group["avg_ticket"]

        group["baseline_txn"] = baseline_txn
        group["txn_ratio_1w"] = transactions / baseline_txn

        transactions_mean_4w = transactions.rolling(4).mean()
        group["txn_ratio_4w"] = transactions_mean_4w / baseline_txn

        last_two_weeks = transactions.rolling(2).mean()
        two_weeks_before = last_two_weeks.shift(2)
        group["txn_trend_4w"] = (last_two_weeks - two_weeks_before) / baseline_txn

        group["volume_mean_4w"] = volume.rolling(4).mean()
        group["volume_ratio_4w"] = group["volume_mean_4w"] / baseline_volume
        previous_volume_mean = group["volume_mean_4w"].shift(4)
        group["volume_growth_4w"] = group["volume_mean_4w"] / previous_volume_mean - 1.0

        group["ticket_ratio_4w"] = ticket.rolling(4).mean() / baseline_ticket

        group["active_days_1w"] = group["active_days"]
        group["active_days_4w"] = group["active_days"].rolling(4).mean()

        group["stockout_hours_4w"] = group["stockout_hours"].rolling(4).sum()
        open_hours_4w = group["open_hours"].rolling(4).sum()
        group["stockout_rate_4w"] = group["stockout_hours_4w"] / open_hours_4w
        group["unserved_4w"] = group["unserved_bdt"].rolling(4).sum()

        transactions_std_4w = transactions.rolling(4).std()
        group["txn_volatility_4w"] = transactions_std_4w / transactions_mean_4w

        pieces.append(group)

    features = pd.concat(pieces, ignore_index=True)
    features = features.merge(agent_info, on="agent_id", how="left")

    # Compare every agent with similar agents (same type) in the same week. This removes network-wide
    # swings such as Eid weeks, so a holiday dip is not mistaken for an agent that is leaving.
    group_keys = ["week_index", "archetype"]
    median_ratio_1w = features.groupby(group_keys)["txn_ratio_1w"].transform("median")
    median_ratio_4w = features.groupby(group_keys)["txn_ratio_4w"].transform("median")
    median_trend = features.groupby(group_keys)["txn_trend_4w"].transform("median")
    features["txn_ratio_1w_vs_peers"] = features["txn_ratio_1w"] / median_ratio_1w.clip(lower=0.05)
    features["txn_ratio_4w_vs_peers"] = features["txn_ratio_4w"] / median_ratio_4w.clip(lower=0.05)
    features["txn_trend_vs_peers"] = features["txn_trend_4w"] - median_trend

    features["archetype_code"] = features["archetype"].map(ARCHETYPE_CODES)
    features["area_code"] = features["area_type"].map(AREA_CODES)

    # the first weeks only exist to build the baseline
    features = features[features["week_index"] >= BASELINE_WEEKS]
    features = features.reset_index(drop=True)
    return features
