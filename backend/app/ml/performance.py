"""B4 - Agent performance intelligence.

Input : one row per agent for ONE week (from the feature table).
Output: for every agent a performance score, peer percentile, growth, service-gap numbers,
        flags (DECLINING, SERVICE_GAP, EMERGING_HIGH_PERFORMER, TOP_PERFORMER),
        one main segment and a cluster name.

Two things make this fair:
  * agents are compared with PEERS OF THE SAME TYPE (urban market, garment zone, ...),
  * growth is measured relative to the peer median, so network-wide swings
    (Eid, salary week, rain) do not make every agent look like a "riser" or a "decliner".
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ---- thresholds (edit here to change the behaviour)
EMERGING_RELATIVE_GROWTH = 0.12      # 12% faster than peers
DECLINING_RELATIVE_GROWTH = -0.15    # 15% slower than peers
TOP_PERCENTILE = 85.0
EMERGING_MIN_PERCENTILE = 50.0
SERVICE_GAP_STOCKOUT_RATE = 0.08     # out of cash/float for 8% of open hours
SERVICE_GAP_MIN_PERCENTILE = 40.0    # only count it as a "gap" if demand is healthy

# ---- score weights (must add up to 1.0)
WEIGHT_VOLUME = 0.45
WEIGHT_GROWTH = 0.25
WEIGHT_SERVICE = 0.20
WEIGHT_CONSISTENCY = 0.10

NUMBER_OF_CLUSTERS = 4


def clip_value(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def growth_score(relative_growth):
    """0% relative growth = 50 points, +50% = 100 points, -50% = 0 points."""
    return clip_value(50.0 + 100.0 * relative_growth, 0.0, 100.0)


def service_score(stockout_rate):
    """No stockouts = 100 points, 15% of hours or more = 0 points."""
    return 100.0 * (1.0 - clip_value(stockout_rate / 0.15, 0.0, 1.0))


def consistency_score(volatility):
    """Stable weeks = 100 points, very unstable (50% swings) = 0 points."""
    return 100.0 * (1.0 - clip_value(volatility / 0.5, 0.0, 1.0))


def choose_flags(volume_percentile, relative_growth, stockout_rate):
    flags = []
    if relative_growth <= DECLINING_RELATIVE_GROWTH:
        flags.append("DECLINING")
    if stockout_rate >= SERVICE_GAP_STOCKOUT_RATE and volume_percentile >= SERVICE_GAP_MIN_PERCENTILE:
        flags.append("SERVICE_GAP")
    if relative_growth >= EMERGING_RELATIVE_GROWTH and volume_percentile >= EMERGING_MIN_PERCENTILE:
        flags.append("EMERGING_HIGH_PERFORMER")
    if volume_percentile >= TOP_PERCENTILE and relative_growth > DECLINING_RELATIVE_GROWTH:
        flags.append("TOP_PERFORMER")
    return flags


def choose_main_segment(flags):
    """One label per agent. The most urgent flag wins."""
    priority_order = ["DECLINING", "SERVICE_GAP", "EMERGING_HIGH_PERFORMER", "TOP_PERFORMER"]
    for flag in priority_order:
        if flag in flags:
            return flag
    return "STEADY"


def recommended_action(segment):
    if segment == "DECLINING":
        return "Call or visit this week: volume is falling faster than similar agents. Ask what changed."
    if segment == "SERVICE_GAP":
        return "Fix supply first: this agent has strong demand but often runs out of cash or e-float. Prioritise top-ups."
    if segment == "EMERGING_HIGH_PERFORMER":
        return "Support the growth: make sure liquidity keeps up, and consider recognition or a training slot."
    if segment == "TOP_PERFORMER":
        return "Protect and learn from: keep service levels high and capture what this agent does well."
    return "No special action. Keep monitoring."


# ---------------------------------------------------------------- clustering
def name_clusters(table, cluster_ids):
    """Gives each KMeans cluster a readable name, using the average values of its members."""
    averages = table.groupby("cluster_id")[["volume_percentile", "relative_growth", "stockout_rate_4w"]].mean()
    remaining = list(cluster_ids)
    names = {}

    # 1) the cluster with the highest volume
    best_cluster = remaining[0]
    for cluster_id in remaining:
        if averages.loc[cluster_id, "volume_percentile"] > averages.loc[best_cluster, "volume_percentile"]:
            best_cluster = cluster_id
    names[best_cluster] = "High-volume core"
    remaining.remove(best_cluster)

    # 2) among the rest, the cluster with the most stockouts
    best_cluster = remaining[0]
    for cluster_id in remaining:
        if averages.loc[cluster_id, "stockout_rate_4w"] > averages.loc[best_cluster, "stockout_rate_4w"]:
            best_cluster = cluster_id
    names[best_cluster] = "Supply-constrained"
    remaining.remove(best_cluster)

    # 3) among the rest, the cluster with the highest average growth (a GROUP label: single agents inside can differ)
    best_cluster = remaining[0]
    for cluster_id in remaining:
        if averages.loc[cluster_id, "relative_growth"] > averages.loc[best_cluster, "relative_growth"]:
            best_cluster = cluster_id
    names[best_cluster] = "Growth-leaning group"
    remaining.remove(best_cluster)

    # 4) whatever is left
    for cluster_id in remaining:
        names[cluster_id] = "Low-activity / watch list"
    return names


def add_clusters(table):
    columns = ["volume_percentile", "relative_growth", "stockout_rate_4w", "txn_volatility_4w"]
    scaler = StandardScaler()
    scaled_values = scaler.fit_transform(table[columns])

    kmeans = KMeans(n_clusters=NUMBER_OF_CLUSTERS, n_init=10, random_state=42)
    table["cluster_id"] = kmeans.fit_predict(scaled_values)

    cluster_ids = sorted(table["cluster_id"].unique())
    names = name_clusters(table, cluster_ids)
    table["cluster_name"] = table["cluster_id"].map(names)
    return table


# ---------------------------------------------------------------- main function
def score_performance(week_rows):
    """week_rows: feature-table rows of ONE week (all agents)."""
    table = week_rows[["agent_id", "archetype", "volume_mean_4w", "volume_growth_4w",
                       "stockout_rate_4w", "unserved_4w", "txn_volatility_4w"]].copy()
    table = table.reset_index(drop=True)

    # missing values (very early weeks) become neutral numbers
    table["volume_growth_4w"] = table["volume_growth_4w"].fillna(0.0)
    table["stockout_rate_4w"] = table["stockout_rate_4w"].fillna(0.0)
    table["unserved_4w"] = table["unserved_4w"].fillna(0.0)
    table["txn_volatility_4w"] = table["txn_volatility_4w"].fillna(0.0)

    # rank inside the peer group, 0-100
    ranks = table.groupby("archetype")["volume_mean_4w"].rank(pct=True)
    table["volume_percentile"] = ranks * 100.0

    # growth relative to the peer median
    peer_median_growth = table.groupby("archetype")["volume_growth_4w"].transform("median")
    table["relative_growth"] = table["volume_growth_4w"] - peer_median_growth

    scores = []
    flag_lists = []
    segments = []
    actions = []
    for row_number in range(len(table)):
        percentile = float(table.loc[row_number, "volume_percentile"])
        growth = float(table.loc[row_number, "relative_growth"])
        stockout_rate = float(table.loc[row_number, "stockout_rate_4w"])
        volatility = float(table.loc[row_number, "txn_volatility_4w"])

        score = (WEIGHT_VOLUME * percentile
                 + WEIGHT_GROWTH * growth_score(growth)
                 + WEIGHT_SERVICE * service_score(stockout_rate)
                 + WEIGHT_CONSISTENCY * consistency_score(volatility))
        flags = choose_flags(percentile, growth, stockout_rate)
        segment = choose_main_segment(flags)

        scores.append(round(score, 1))
        flag_lists.append(flags)
        segments.append(segment)
        actions.append(recommended_action(segment))

    table["performance_score"] = scores
    table["flags"] = flag_lists
    table["segment"] = segments
    table["recommended_action"] = actions

    table = add_clusters(table)
    table = table.rename(columns={"volume_mean_4w": "avg_weekly_volume_bdt", "unserved_4w": "lost_volume_4w_bdt"})
    return table
