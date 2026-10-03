"""Builds the weekly agent activity table.

Step 1  aggregate the existing hourly table into one row per agent per full week (SQL).
Step 2  add a SYNTHETIC churn overlay: some agents slowly lose activity and go quiet.
        The overlay only changes the weekly table. The hourly / daily tables and the
        trained liquidity models are NOT touched.
Step 3  save the result into the agent_weekly table.
"""
import io

import numpy as np
import pandas as pd

from app.db.queries import fetch_df

OPEN_HOURS_PER_WEEK = 7 * 16        # 16 open hours per day, 7 days

WEEKLY_SQL = """
SELECT
    agent_id,
    date_trunc('week', "timestamp")::date AS week_start,
    SUM(cash_out_cnt + cash_in_cnt)       AS txn_count,
    SUM(cash_out_amt + cash_in_amt)       AS volume_bdt,
    COUNT(DISTINCT "timestamp"::date) FILTER (WHERE cash_out_cnt + cash_in_cnt > 0) AS active_days,
    SUM(CASE WHEN stockout THEN 1 ELSE 0 END) AS stockout_hours,
    SUM(unserved_amt)                     AS unserved_bdt,
    COUNT(*)                              AS open_hours
FROM hourly
GROUP BY agent_id, date_trunc('week', "timestamp")
ORDER BY agent_id, week_start
"""

TABLE_COLUMNS = [
    "agent_id", "week_start", "week_index", "txn_count", "volume_bdt", "avg_ticket",
    "active_days", "stockout_hours", "unserved_bdt", "open_hours", "episode_type",
]


# ---------------------------------------------------------------- step 1: aggregate
async def read_weekly_from_hourly(db):
    """Aggregate the hourly table. Partial weeks (first and last) are dropped."""
    raw = await fetch_df(db, WEEKLY_SQL, parse_dates=["week_start"], big=True)

    full_weeks = raw[raw["open_hours"] == OPEN_HOURS_PER_WEEK]
    weekly = full_weeks.copy()

    # make sure money and count columns are floats, so the churn overlay can scale them
    weekly["txn_count"] = weekly["txn_count"].astype(float)
    weekly["volume_bdt"] = weekly["volume_bdt"].astype(float)
    weekly["unserved_bdt"] = weekly["unserved_bdt"].astype(float)

    # week_index: 0 for the first full week, 1 for the next, and so on
    weekly["week_index"] = weekly["week_start"].rank(method="dense").astype(int) - 1

    # average ticket size (volume per transaction), 0 when there were no transactions
    weekly["avg_ticket"] = 0.0
    has_transactions = weekly["txn_count"] > 0
    weekly.loc[has_transactions, "avg_ticket"] = (
        weekly.loc[has_transactions, "volume_bdt"] / weekly.loc[has_transactions, "txn_count"]
    )
    weekly["episode_type"] = "none"
    return weekly.reset_index(drop=True)


# ---------------------------------------------------------------- step 2: churn overlay
def decay_multiplier(week_index, start_week, decay_weeks, rng):
    """1.0 before the churn starts, then a straight-line fall to about 3% of normal activity."""
    if week_index < start_week:
        return 1.0

    weeks_into_decay = week_index - start_week + 1
    multiplier = 1.0 - weeks_into_decay / decay_weeks
    if multiplier < 0.03:
        multiplier = 0.03

    noise = rng.normal(1.0, 0.04)
    return multiplier * noise


def choose_churning_agents(weekly, rng):
    """ASSUMPTION: agents that often run out of cash or float lose customers more often.
    churn probability = 5% + 2 x (share of open hours with a stockout), capped at 50%."""
    totals = weekly.groupby("agent_id").agg(
        stockout_hours=("stockout_hours", "sum"),
        open_hours=("open_hours", "sum"),
    )

    churning_agents = []
    for agent_id in totals.index:
        stockout_rate = totals.loc[agent_id, "stockout_hours"] / totals.loc[agent_id, "open_hours"]
        churn_probability = 0.05 + 2.0 * stockout_rate
        if churn_probability > 0.5:
            churn_probability = 0.5

        random_draw = rng.random()
        if random_draw < churn_probability:
            churning_agents.append(int(agent_id))
    return churning_agents


def add_churn_overlay(weekly, seed=7):
    """Returns (weekly_with_overlay, list_of_churning_agent_ids)."""
    rng = np.random.default_rng(seed)
    number_of_weeks = int(weekly["week_index"].max()) + 1
    churning_agents = choose_churning_agents(weekly, rng)

    for agent_id in churning_agents:
        # churn starts between week 10 and 4 weeks before the end, so some agents are still
        # mid-decline near the end of the data (this is what the early-warning model must catch)
        start_week = int(rng.integers(10, number_of_weeks - 4))
        decay_weeks = int(rng.integers(4, 9))

        agent_rows = weekly[weekly["agent_id"] == agent_id]
        for row_label in agent_rows.index:
            week_index = int(weekly.loc[row_label, "week_index"])
            multiplier = decay_multiplier(week_index, start_week, decay_weeks, rng)
            if multiplier >= 1.0:
                continue

            weekly.loc[row_label, "txn_count"] = weekly.loc[row_label, "txn_count"] * multiplier
            weekly.loc[row_label, "volume_bdt"] = weekly.loc[row_label, "volume_bdt"] * multiplier

            day_share = multiplier * 1.5
            if day_share > 1.0:
                day_share = 1.0
            weekly.loc[row_label, "active_days"] = int(round(weekly.loc[row_label, "active_days"] * day_share))
            weekly.loc[row_label, "episode_type"] = "churn"

    return weekly, churning_agents


def growth_multiplier(week_index, start_week, ramp_weeks, final_boost):
    """1.0 before the growth starts, then a straight-line rise to (1 + final_boost) and it stays there."""
    if week_index < start_week:
        return 1.0
    weeks_into_ramp = week_index - start_week + 1
    progress = weeks_into_ramp / ramp_weeks
    if progress > 1.0:
        progress = 1.0
    return 1.0 + final_boost * progress


def add_growth_overlay(weekly, churning_agents, seed=11):
    """About 10% of the agents that are NOT churning grow strongly (more customers, better location, ...).
    These are the 'emerging high performers' that B4 should find."""
    rng = np.random.default_rng(seed)
    number_of_weeks = int(weekly["week_index"].max()) + 1

    growing_agents = []
    for agent_id in sorted(weekly["agent_id"].unique()):
        if int(agent_id) in churning_agents:
            continue
        random_draw = rng.random()
        if random_draw < 0.10:
            growing_agents.append(int(agent_id))

    for agent_id in growing_agents:
        start_week = int(rng.integers(10, number_of_weeks - 6))
        ramp_weeks = 6
        final_boost = float(rng.uniform(0.35, 0.70))

        agent_rows = weekly[weekly["agent_id"] == agent_id]
        for row_label in agent_rows.index:
            week_index = int(weekly.loc[row_label, "week_index"])
            multiplier = growth_multiplier(week_index, start_week, ramp_weeks, final_boost)
            if multiplier <= 1.0:
                continue
            weekly.loc[row_label, "txn_count"] = weekly.loc[row_label, "txn_count"] * multiplier
            weekly.loc[row_label, "volume_bdt"] = weekly.loc[row_label, "volume_bdt"] * multiplier
            weekly.loc[row_label, "episode_type"] = "growth"

    return weekly, growing_agents


# ---------------------------------------------------------------- step 3: save / load
async def save_weekly_table(db, weekly):
    await db.execute("TRUNCATE agent_weekly")
    csv_text = weekly[TABLE_COLUMNS].to_csv(index=False, header=False)
    await db.copy_to_table(
        "agent_weekly",
        source=io.BytesIO(csv_text.encode()),
        columns=TABLE_COLUMNS,
        format="csv",
    )


async def load_weekly_table(db):
    query = "SELECT * FROM agent_weekly ORDER BY agent_id, week_index"
    weekly = await fetch_df(db, query, parse_dates=["week_start"], big=True)
    return weekly
