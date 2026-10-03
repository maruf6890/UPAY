"""Login, token refresh, logout, who-am-i and change-password."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import repository
from app.auth.deps import get_current_user
from app.auth.schemas import (ChangePasswordRequest, CurrentUser, LoginRequest, RefreshRequest, TokenResponse)
from app.auth.security import (AuthError, burn_time, create_token, decode_token, hash_password, verify_password)
from app.core.config import get_settings
from app.db.queries import log_audit

router = APIRouter(prefix="/auth", tags=["auth"])

BAD_LOGIN = "Incorrect username or password"


def bad_login_error():
    return HTTPException(status_code=401, detail=BAD_LOGIN, headers={"WWW-Authenticate": "Bearer"})


def client_ip(request):
    if request.client is None:
        return "unknown"
    return request.client.host


def user_from_row(row):
    return CurrentUser(id=row["id"], username=row["username"], full_name=row["full_name"], role=row["role"],
                       district=row["district"], agent_code=row["agent_code"])


async def issue_tokens(pool, settings, row):
    access_token, access_jti, access_expires = create_token(settings, row, "access")
    refresh_token, refresh_jti, refresh_expires = create_token(settings, row, "refresh")
    await repository.store_refresh_token(pool, refresh_jti, row["id"], refresh_expires)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_minutes * 60,
        user=user_from_row(row),
    )


async def do_login(request, username, password):
    settings = get_settings()
    pool = request.app.state.ctx.pool
    ip = client_ip(request)
    now = datetime.now(timezone.utc)

    row = await repository.get_user_by_username(pool, username)
    if row is None:
        burn_time(password)
        await log_audit(pool, username[0:64], "login_failed", {"ip": ip, "reason": "unknown_user"})
        raise bad_login_error()

    if row["locked_until"] is not None and row["locked_until"] > now:
        await log_audit(pool, row["username"], "login_blocked", {"ip": ip, "reason": "account_locked"})
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")

    if not verify_password(password, row["password_hash"]):
        result = await repository.record_login_failure(pool, row["id"], settings.max_failed_logins, settings.lockout_minutes)
        reason = "bad_password"
        if result["locked_until"] is not None and result["locked_until"] > now:
            reason = "bad_password_account_now_locked"
        await log_audit(pool, row["username"], "login_failed", {"ip": ip, "reason": reason})
        raise bad_login_error()

    if not row["is_active"]:
        await log_audit(pool, row["username"], "login_failed", {"ip": ip, "reason": "account_disabled"})
        raise bad_login_error()

    await repository.record_login_success(pool, row["id"])
    await log_audit(pool, row["username"], "login_success", {"ip": ip, "role": row["role"]})
    return await issue_tokens(pool, settings, row)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """Log in with JSON: {"username": "...", "password": "..."}. Returns an access token and a refresh token."""
    return await do_login(request, body.username, body.password)


@router.post("/token", response_model=TokenResponse, include_in_schema=True)
async def login_form(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    """Same login, but as a form. This is what the 'Authorize' button in /docs uses."""
    return await do_login(request, form.username, form.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, request: Request):
    """Swap a refresh token for a new access token AND a new refresh token. Each refresh token works only once."""
    settings = get_settings()
    pool = request.app.state.ctx.pool
    ip = client_ip(request)

    try:
        claims = decode_token(settings, body.refresh_token, "refresh")
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error), headers={"WWW-Authenticate": "Bearer"})

    stored = await repository.get_refresh_token(pool, claims["jti"])
    if stored is None:
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})

    first_use = await repository.claim_refresh_token(pool, claims["jti"])
    if not first_use:
        # this token was already used or revoked: somebody may have stolen it, so end every session of this user
        await repository.revoke_all_refresh_tokens(pool, stored["user_id"])
        await log_audit(pool, claims.get("username", "unknown"), "refresh_token_reuse", {"ip": ip})
        raise HTTPException(status_code=401, detail="Refresh token was already used. Please log in again.",
                            headers={"WWW-Authenticate": "Bearer"})

    row = await repository.get_user_by_id(pool, stored["user_id"])
    if row is None or not row["is_active"]:
        raise HTTPException(status_code=401, detail="User is not active", headers={"WWW-Authenticate": "Bearer"})

    return await issue_tokens(pool, settings, row)


@router.post("/logout")
async def logout(body: RefreshRequest, request: Request):
    """Ends the session by revoking the refresh token. The access token simply expires on its own."""
    settings = get_settings()
    pool = request.app.state.ctx.pool
    try:
        claims = decode_token(settings, body.refresh_token, "refresh")
        await repository.claim_refresh_token(pool, claims["jti"])
        await log_audit(pool, claims.get("username", "unknown"), "logout", {"ip": client_ip(request)})
    except AuthError:
        pass                                        # an invalid or expired token is already useless: nothing to revoke
    return {"message": "Logged out"}


@router.get("/me", response_model=CurrentUser)
async def me(user: CurrentUser = Depends(get_current_user)):
    """Who am I? Use this after login to decide what the frontend shows."""
    return user


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, request: Request, user: CurrentUser = Depends(get_current_user)):
    pool = request.app.state.ctx.pool
    row = await repository.get_user_by_id(pool, user.id)

    if not verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="The new password must be different")

    try:
        new_hash = hash_password(body.new_password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    await repository.set_password(pool, user.id, new_hash)
    await repository.revoke_all_refresh_tokens(pool, user.id)        # every other device must log in again
    await log_audit(pool, user.username, "password_changed", {"ip": client_ip(request)})
    return {"message": "Password changed. Please log in again on your other devices."}
