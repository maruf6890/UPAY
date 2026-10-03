-- migrate:up
CREATE TABLE agents (
    agent_id      INTEGER PRIMARY KEY,
    agent_code    VARCHAR(10) NOT NULL UNIQUE,
    division      VARCHAR(40) NOT NULL,
    district      VARCHAR(40) NOT NULL,
    archetype     VARCHAR(32) NOT NULL CHECK (archetype IN ('urban_market','garment_zone','rural_remittance','transit_hub')),
    area_type     VARCHAR(16) NOT NULL CHECK (area_type IN ('urban','semi_urban','rural')),
    lat           DOUBLE PRECISION,
    lon           DOUBLE PRECISION,
    base_rate     DOUBLE PRECISION,
    avg_txn_size  DOUBLE PRECISION,
    out_share     DOUBLE PRECISION,
    haat_day1     SMALLINT,
    haat_day2     SMALLINT,
    growth        DOUBLE PRECISION,
    cash_target   DOUBLE PRECISION,
    float_target  DOUBLE PRECISION
);
CREATE INDEX ix_agents_district ON agents (district);

-- one row per agent per OPEN hour (07:00-22:00); timestamp = start of the hour
CREATE TABLE hourly (
    agent_id      INTEGER   NOT NULL REFERENCES agents (agent_id),
    "timestamp"   TIMESTAMP NOT NULL,
    cash_out_cnt  REAL,
    cash_in_cnt   REAL,
    cash_out_amt  REAL,
    cash_in_amt   REAL,
    cash_balance  REAL,
    float_balance REAL,
    stockout      BOOLEAN,
    unserved_amt  REAL,
    PRIMARY KEY (agent_id, "timestamp")
);
CREATE INDEX ix_hourly_ts ON hourly ("timestamp");

CREATE TABLE daily (
    agent_id                  INTEGER NOT NULL REFERENCES agents (agent_id),
    date                      DATE    NOT NULL,
    txn_count                 REAL,
    out_amt                   REAL,
    in_amt                    REAL,
    avg_txn_size              REAL,
    out_in_ratio              REAL,
    peak_hour_share           REAL,
    near_threshold_share      REAL,
    repeat_counterparty_share REAL,
    night_txn_cnt             REAL,
    round_amount_share        REAL,
    is_anomaly                BOOLEAN,      -- synthetic ground truth: evaluation only, never a model feature
    anomaly_type              VARCHAR(32),
    PRIMARY KEY (agent_id, date)
);

CREATE TABLE weather (
    date     DATE        NOT NULL,
    division VARCHAR(40) NOT NULL,
    rain_mm  REAL,
    rain_3d  REAL,
    PRIMARY KEY (date, division)
);

CREATE TABLE anomaly_labels (               -- injected synthetic episodes (evaluation only)
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id   INTEGER NOT NULL REFERENCES agents (agent_id),
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    type       VARCHAR(32) NOT NULL,
    strength   DOUBLE PRECISION
);

-- migrate:down
DROP TABLE IF EXISTS anomaly_labels;
DROP TABLE IF EXISTS weather;
DROP TABLE IF EXISTS daily;
DROP TABLE IF EXISTS hourly;
DROP TABLE IF EXISTS agents;
