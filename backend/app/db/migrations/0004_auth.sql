-- migrate:up
CREATE TABLE users (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username        VARCHAR(64)  NOT NULL,
    password_hash   TEXT         NOT NULL,             -- bcrypt, never the password
    full_name       VARCHAR(120) NOT NULL,
    role            VARCHAR(16)  NOT NULL CHECK (role IN ('manager', 'agent', 'analyst')),
    district        VARCHAR(40),                       -- manager scope. NULL = all districts
    agent_code      VARCHAR(10),                       -- the agent this login belongs to (role 'agent')
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    failed_attempts INTEGER      NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT agent_login_needs_agent_code CHECK (role <> 'agent' OR agent_code IS NOT NULL)
);
-- usernames are unique ignoring case ("Manager" and "manager" are the same person)
CREATE UNIQUE INDEX ux_users_username ON users (lower(username));
-- NOTE: no foreign key from users.agent_code to agents on purpose.
-- scripts.generate_data runs TRUNCATE agents ... CASCADE, which would silently delete every user account.

CREATE TABLE refresh_tokens (
    jti        UUID PRIMARY KEY,                       -- the token's unique id (also inside the JWT)
    user_id    INTEGER     NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,                            -- set on logout, on use (rotation) and on password change
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_tokens_user ON refresh_tokens (user_id);

-- migrate:down
DROP TABLE IF EXISTS refresh_tokens;
DROP TABLE IF EXISTS users;
