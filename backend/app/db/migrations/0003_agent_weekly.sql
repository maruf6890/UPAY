-- migrate:up
-- Weekly activity per agent. Input for B4 (performance intelligence) and B7 (churn prediction).
-- Built from the existing hourly table by: python3 -m scripts.build_agent_weekly
CREATE TABLE agent_weekly (
    agent_id         INTEGER  NOT NULL REFERENCES agents (agent_id),
    week_start       DATE     NOT NULL,          -- Monday of the week
    week_index       SMALLINT NOT NULL,          -- 0 = first full week in the data
    txn_count        REAL,
    volume_bdt       REAL,
    avg_ticket       REAL,
    active_days      SMALLINT,
    stockout_hours   SMALLINT,
    unserved_bdt     REAL,
    open_hours       SMALLINT,
    episode_type     VARCHAR(10) NOT NULL DEFAULT 'none',  -- 'none' | 'churn' | 'growth'. Synthetic ground truth: evaluation only, never a model feature
    PRIMARY KEY (agent_id, week_start)
);
CREATE INDEX ix_agent_weekly_week ON agent_weekly (week_start);

-- migrate:down
DROP TABLE IF EXISTS agent_weekly;
