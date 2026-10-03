"""python3 -m scripts.evaluate_performance

How well does B4 find the agents that the generator really made decline or grow?
(The injected episodes are synthetic ground truth. They are NEVER used as features.)
"""
from app.db.pool import run_with_conn
from app.db.queries import fetch_df
from app.ml.agent_features import build_feature_table
from app.ml.agent_weekly import load_weekly_table
from app.ml.performance import score_performance


async def load_inputs(db):
    weekly = await load_weekly_table(db)
    agents = await fetch_df(db, "SELECT agent_id, archetype, area_type FROM agents ORDER BY agent_id")
    return weekly, agents


def first_week_of_episode(weekly, episode_type):
    """agent_id -> first week_index that belongs to that kind of episode."""
    rows = weekly[weekly["episode_type"] == episode_type]
    first_weeks = {}
    for agent_id, group in rows.groupby("agent_id"):
        first_weeks[int(agent_id)] = int(group["week_index"].min())
    return first_weeks


def main():
    weekly, agents = run_with_conn(load_inputs)
    features = build_feature_table(weekly, agents)
    churn_start = first_week_of_episode(weekly, "churn")
    growth_start = first_week_of_episode(weekly, "growth")
    last_week = int(features["week_index"].max())

    declining_hits = 0
    declining_flagged = 0
    declining_truth = 0
    emerging_hits = 0
    emerging_flagged = 0
    emerging_truth = 0

    # look at the last 12 weeks; a "true" decline / rise is one that started within the previous 6 weeks
    for week_index in range(last_week - 11, last_week + 1):
        rows = features[features["week_index"] == week_index]
        scored = score_performance(rows)

        for row_number in range(len(scored)):
            agent_id = int(scored.iloc[row_number]["agent_id"])
            flags = scored.iloc[row_number]["flags"]

            is_declining_truth = False
            if agent_id in churn_start:
                weeks_since_start = week_index - churn_start[agent_id]
                if 0 <= weeks_since_start <= 6:
                    is_declining_truth = True

            is_emerging_truth = False
            if agent_id in growth_start:
                weeks_since_start = week_index - growth_start[agent_id]
                if 0 <= weeks_since_start <= 6:
                    is_emerging_truth = True

            if is_declining_truth:
                declining_truth = declining_truth + 1
            if is_emerging_truth:
                emerging_truth = emerging_truth + 1

            if "DECLINING" in flags:
                declining_flagged = declining_flagged + 1
                if is_declining_truth:
                    declining_hits = declining_hits + 1
            if "EMERGING_HIGH_PERFORMER" in flags:
                emerging_flagged = emerging_flagged + 1
                if is_emerging_truth:
                    emerging_hits = emerging_hits + 1

    print("Agent-weeks checked over the last 12 weeks")
    print("DECLINING flag : precision", round(declining_hits / max(declining_flagged, 1), 2),
          "| recall", round(declining_hits / max(declining_truth, 1), 2),
          f"({declining_hits} hits, {declining_flagged} flagged, {declining_truth} truly declining)")
    print("EMERGING flag  : precision", round(emerging_hits / max(emerging_flagged, 1), 2),
          "| recall", round(emerging_hits / max(emerging_truth, 1), 2),
          f"({emerging_hits} hits, {emerging_flagged} flagged, {emerging_truth} truly growing)")


if __name__ == "__main__":
    main()
