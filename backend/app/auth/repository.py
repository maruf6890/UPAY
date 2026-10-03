"""All SQL for users and refresh tokens (raw asyncpg, same style as the rest of the project)."""


# ---------------------------------------------------------------- users
async def get_user_by_username(pool, username):
    return await pool.fetchrow("SELECT * FROM users WHERE lower(username) = lower($1)", username)


async def get_user_by_id(pool, user_id):
    return await pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)


async def create_user(pool, username, password_hash, full_name, role, district, agent_code):
    return await pool.fetchrow(
        """INSERT INTO users (username, password_hash, full_name, role, district, agent_code)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
        username, password_hash, full_name, role, district, agent_code)


async def list_users(pool):
    return await pool.fetch(
        "SELECT id, username, full_name, role, district, agent_code, is_active, locked_until, last_login_at "
        "FROM users ORDER BY id")


async def set_password(pool, user_id, password_hash):
    await pool.execute("UPDATE users SET password_hash = $2, failed_attempts = 0, locked_until = NULL WHERE id = $1",
                       user_id, password_hash)


async def set_active(pool, user_id, is_active):
    await pool.execute("UPDATE users SET is_active = $2 WHERE id = $1", user_id, is_active)


async def unlock(pool, user_id):
    await pool.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = $1", user_id)


# ---------------------------------------------------------------- login bookkeeping
async def record_login_success(pool, user_id):
    await pool.execute(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login_at = now() WHERE id = $1", user_id)


async def record_login_failure(pool, user_id, max_failed, lockout_minutes):
    """Adds one failed attempt. When the limit is reached the account is locked and the counter restarts."""
    return await pool.fetchrow(
        """UPDATE users
           SET failed_attempts = CASE WHEN failed_attempts + 1 >= $2 THEN 0 ELSE failed_attempts + 1 END,
               locked_until    = CASE WHEN failed_attempts + 1 >= $2
                                      THEN now() + make_interval(mins => $3) ELSE locked_until END
           WHERE id = $1
           RETURNING failed_attempts, locked_until""",
        user_id, max_failed, lockout_minutes)


# ---------------------------------------------------------------- refresh tokens
async def store_refresh_token(pool, jti, user_id, expires_at):
    await pool.execute("INSERT INTO refresh_tokens (jti, user_id, expires_at) VALUES ($1::uuid, $2, $3)",
                       jti, user_id, expires_at)


async def get_refresh_token(pool, jti):
    return await pool.fetchrow("SELECT * FROM refresh_tokens WHERE jti = $1::uuid", jti)


async def claim_refresh_token(pool, jti):
    """Marks a refresh token as used. Returns True only for the FIRST caller, so one token can never be used twice."""
    row = await pool.fetchrow(
        "UPDATE refresh_tokens SET revoked_at = now() WHERE jti = $1::uuid AND revoked_at IS NULL RETURNING jti", jti)
    return row is not None


async def revoke_all_refresh_tokens(pool, user_id):
    await pool.execute("UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = $1 AND revoked_at IS NULL", user_id)
