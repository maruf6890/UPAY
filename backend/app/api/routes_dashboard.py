"""One dashboard endpoint. The content depends on the role of the logged-in user."""
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.deps import get_current_user
from app.auth.schemas import CurrentUser
from app.core.utils import clean

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(request: Request, as_of: str | None = None, user: CurrentUser = Depends(get_current_user)):
    """The single dashboard. Same URL for everybody; a manager, an agent and an analyst each get different widgets."""
    service = getattr(request.app.state, "dashboard", None)
    if service is None:
        raise HTTPException(503, "Dashboard service is not loaded")
    try:
        return clean(await service.build(user, as_of))
    except ValueError as error:
        raise HTTPException(400, str(error))
