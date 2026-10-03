-- migrate:up
CREATE TABLE alert_reviews (                -- current analyst decision per alert
    alert_id    VARCHAR(40) PRIMARY KEY,
    status      VARCHAR(16) NOT NULL CHECK (status IN ('confirmed','dismissed')),
    reviewer    VARCHAR(64) NOT NULL,
    note        TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE feedback_log (                 -- append-only: every decision becomes a future training label
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id   VARCHAR(40) NOT NULL,
    decision   VARCHAR(16) NOT NULL,
    reviewer   VARCHAR(64),
    note       TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_feedback_alert ON feedback_log (alert_id);

CREATE TABLE audit_log (
    id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor  VARCHAR(64),
    action VARCHAR(64) NOT NULL,
    detail JSONB
);
CREATE INDEX ix_audit_ts ON audit_log (ts);

CREATE TABLE model_runs (                   -- metrics + calibration of every training run
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    metrics     JSONB NOT NULL,
    calibration JSONB NOT NULL
);

-- migrate:down
DROP TABLE IF EXISTS model_runs;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS feedback_log;
DROP TABLE IF EXISTS alert_reviews;
