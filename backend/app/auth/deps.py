"""FastAPI dependencies that decide WHO is calling.

login_required   : put on a whole router. Every route under it needs a valid access token (except PUBLIC_PATHS).
get_current_user : use inside a route when you need to know who is calling.
require_roles    : OPTIONAL. Not used anywhere yet. See the integration guide if you later want to restrict routes by role.
"""
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

from app.auth import repository
from app.auth.schemas import CurrentUser
from app.auth.security import AuthError, decode_token
from app.core.config import get_settings

# tokenUrl makes the "Authorize" button appear in /docs. That endpoint accepts a normal username + password form.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

PUBLIC_PATHS = ["/health"]


def unauthorized(message):
    return HTTPException(status_code=401, detail=message, headers={"WWW-Authenticate": "Bearer"})


async def authenticate(request: Request, token):
    """Checks the token, then loads the user from the database (so a disabled user is blocked immediately)."""
    already_checked = getattr(request.state, "user", None)
    if already_checked is not None:
        return already_checked

    if token is None:
        raise unauthorized("Not authenticated")

    try:
        claims = decode_token(get_settings(), token, "access")
        user_id = int(claims["sub"])
    except (AuthError, ValueError) as error:
        raise unauthorized(str(error))

    row = await repository.get_user_by_id(request.app.state.ctx.pool, user_id)
    if row is None or not row["is_active"]:
        raise unauthorized("User is not active")

    user = CurrentUser(id=row["id"], username=row["username"], full_name=row["full_name"], role=row["role"],
                       district=row["district"], agent_code=row["agent_code"])
    request.state.user = user
    return user


async def login_required(request: Request, token: str | None = Depends(oauth2_scheme)):
    if request.url.path in PUBLIC_PATHS:
        return
    await authenticate(request, token)


async def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> CurrentUser:
    return await authenticate(request, token)


def require_roles(*allowed_roles):
    """OPTIONAL and currently unused. Example for later:
        router = APIRouter(dependencies=[Depends(require_roles("manager"))])
    """
    async def check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Your role cannot use this endpoint")
        return user
    return check
