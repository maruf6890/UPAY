#!/bin/sh
# Idempotent first-time setup: schema, synthetic data, demo users, ML artifacts.
set -e
cd /app

python - <<'PY'
import asyncio
from app.db import migrate
from app.db.pool import connect

async def counts():
    await migrate.up()
    conn = await connect()
    try:
        agents = await conn.fetchval("SELECT COUNT(*) FROM agents")
        try:
            weekly = await conn.fetchval("SELECT COUNT(*) FROM agent_weekly")
        except Exception:
            weekly = 0
        return int(agents or 0), int(weekly or 0)
    finally:
        await conn.close()

agents, weekly = asyncio.run(counts())
with open("/tmp/upay_seed_counts", "w", encoding="utf-8") as f:
    f.write(f"{agents} {weekly}\n")
print(f"seed check: agents={agents} agent_weekly={weekly}")
PY

read AGENTS WEEKLY < /tmp/upay_seed_counts

if [ "$AGENTS" = "0" ]; then
  python -m scripts.generate_data
fi

if [ "$AGENTS" = "0" ] || [ "$WEEKLY" = "0" ]; then
  python -m scripts.build_agent_weekly
fi

python -m scripts.create_user demo

if [ ! -f artifacts/liquidity_models.joblib ] || [ ! -f artifacts/anomaly_model.joblib ]; then
  python -m scripts.train
fi

if [ ! -f artifacts/churn_model.joblib ]; then
  python -m scripts.train_churn
fi

echo "Seed finished."
