"""Password hashing (bcrypt) and JWT creation / checking (PyJWT). No database access in this file."""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

MAX_PASSWORD_BYTES = 72          # bcrypt's hard limit
REQUIRED_CLAIMS = ["exp", "iat", "sub", "jti", "type"]
DEFAULT_SECRET_PREFIX = "dev-only-secret"


class AuthError(Exception):
    """Raised for any token problem. The message is safe to show to the caller."""


# ---------------------------------------------------------------- passwords
def hash_password(plain_password):
    data = plain_password.encode("utf-8")
    if len(data) > MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long (maximum 72 bytes)")
    hashed = bcrypt.hashpw(data, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain_password, stored_hash):
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False


_dummy_hash = None


def burn_time(plain_password):
    """Used when the username does not exist: do the same slow bcrypt work, so response time
    does not reveal whether a username is real."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("a-password-nobody-uses")
    verify_password(plain_password, _dummy_hash)


# ---------------------------------------------------------------- tokens
def create_token(settings, user_row, token_type):
    """Returns (token_text, jti, expires_at). token_type is 'access' or 'refresh'."""
    now = datetime.now(timezone.utc)
    if token_type == "access":
        lifetime = timedelta(minutes=settings.access_token_minutes)
    else:
        lifetime = timedelta(days=settings.refresh_token_days)
    expires_at = now + lifetime
    jti = str(uuid.uuid4())

    claims = {
        "sub": str(user_row["id"]),
        "username": user_row["username"],
        "role": user_row["role"],
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti, expires_at


def decode_token(settings, token, expected_type):
    """Checks signature, expiry, required claims and that it is the right kind of token."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],          # fixed list: the 'none' algorithm trick is refused
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")

    if claims.get("type") != expected_type:
        raise AuthError("Wrong kind of token")
    return claims


def check_auth_settings(settings, log=print):
    """Call once at start-up. A weak secret is a warning in development and an error in production."""
    weak = settings.jwt_secret.startswith(DEFAULT_SECRET_PREFIX) or len(settings.jwt_secret) < 32
    if not weak:
        return
    if settings.app_env == "production":
        raise RuntimeError("JWT_SECRET is missing or weak. Set a random value of at least 32 characters in .env")
    log("WARNING: using the default development JWT secret. Set JWT_SECRET in .env before sharing this app.")
