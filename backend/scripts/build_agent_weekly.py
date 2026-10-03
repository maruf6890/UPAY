"""python3 -m scripts.build_agent_weekly

Builds the agent_weekly table from the hourly data (and applies the synthetic churn overlay).
Run it again whenever you re-run scripts.generate_data (that script empties agent_weekly).
"""
import asyncio

from app.db import migrate
from app.db.pool import run_with_conn
from app.ml.agent_weekly import add_churn_overlay, add_growth_overlay, read_weekly_from_hourly, save_weekly_table


async def build(db):
    print("Aggregating hourly data into weekly rows ...")
    weekly = await read_weekly_from_hourly(db)
    print("  full weeks:", int(weekly["week_index"].max()) + 1, "| agents:", weekly["agent_id"].nunique())

    print("Adding the synthetic churn and growth overlays ...")
    weekly, churning_agents = add_churn_overlay(weekly)
    weekly, growing_agents = add_growth_overlay(weekly, churning_agents)
    print("  agents given a churn episode :", len(churning_agents))
    print("  agents given a growth episode:", len(growing_agents))

    print("Saving to PostgreSQL (agent_weekly) ...")
    await save_weekly_table(db, weekly)
    print("  rows saved:", len(weekly))


if __name__ == "__main__":
    print("Applying migrations ...")
    asyncio.run(migrate.up())
    run_with_conn(build)
