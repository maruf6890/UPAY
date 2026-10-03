"""C5 routes: Area Manager Copilot."""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.utils import clean

router = APIRouter(prefix="/copilot", tags=["copilot"])


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300, description="Question in plain English")
    as_of: str | None = Field(default=None, description="Date or date-time, for example 2026-05-20")
    district: str | None = Field(default=None, max_length=40)


def get_service(request: Request):
    service = getattr(request.app.state, "copilot", None)
    if service is None:
        raise HTTPException(503, "Copilot service is not loaded")
    return service


@router.get("/brief")
async def morning_brief(request: Request, as_of: str | None = None, district: str | None = Query(None, max_length=40)):
    """Morning brief with 5 sections. Every item has a drill-down link to the detail endpoint."""
    service = get_service(request)
    try:
        return await service.morning_brief(as_of, district)
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.post("/ask")
async def ask(body: AskRequest, request: Request):
    """Ask a question. The copilot can only call read-only tools, so it cannot change anything."""
    service = get_service(request)
    try:
        return clean(await service.ask(body.question, body.as_of, body.district))
    except ValueError as error:
        raise HTTPException(400, str(error))
