"""C1 routes: coverage gap map. The /coverage/map response is GeoJSON, ready for Leaflet or Mapbox."""
from fastapi import APIRouter, HTTPException, Query, Request

from app.core.utils import clean

router = APIRouter(prefix="/coverage", tags=["coverage-map"])

GAP_PATTERN = "^(CAPACITY_GAP|NO_COVERAGE|UNDER_SERVED|OVER_SUPPLIED|LOW_DEMAND|BALANCED)$"


def get_service(request: Request):
    service = getattr(request.app.state, "coverage", None)
    if service is None:
        raise HTTPException(503, "Coverage service is not loaded")
    return service


@router.get("/map")
async def coverage_map(request: Request, as_of: str | None = None,
                       gap_type: str | None = Query(None, pattern=GAP_PATTERN)):
    """GeoJSON FeatureCollection: one hexagon per feature, coloured by properties.gap_type."""
    service = get_service(request)
    try:
        return clean(await service.map_geojson(as_of, gap_type))
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.get("/gaps")
async def coverage_gaps(request: Request, as_of: str | None = None,
                        gap_type: str | None = Query(None, pattern="^(CAPACITY_GAP|NO_COVERAGE|UNDER_SERVED)$"),
                        limit: int = Query(10, le=100)):
    """Ranked list of the biggest gaps with a recommendation for each."""
    service = get_service(request)
    try:
        gaps = await service.top_gaps(as_of, gap_type, limit)
    except ValueError as error:
        raise HTTPException(400, str(error))
    return clean({"gaps": gaps})


@router.get("/summary")
async def coverage_summary(request: Request, as_of: str | None = None):
    service = get_service(request)
    try:
        return clean(await service.summary(as_of))
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.get("/cells/{h3_id}")
async def coverage_cell(h3_id: str, request: Request, as_of: str | None = None):
    service = get_service(request)
    try:
        detail = await service.cell_detail(h3_id, as_of)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if detail is None:
        raise HTTPException(404, "Hexagon not found")
    return clean(detail)
