from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.models import SearchRequest, SearchResponse
from app.services.earth_search import EarthSearchError, search_sentinel2
from app.services.preview import PreviewError, get_visual_href, render_visual_cog

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="EO Image Check",
    description="Check Google AI provenance and independently compare broad geospatial claims with public Sentinel-2 observations.",
    version="0.4.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    try:
        return await search_sentinel2(request)
    except EarthSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/preview/{item_id}.png")
async def preview(
    item_id: str,
    west: float = Query(ge=-180, le=180),
    south: float = Query(ge=-90, le=90),
    east: float = Query(ge=-180, le=180),
    north: float = Query(ge=-90, le=90),
    max_size: int = Query(default=900, ge=256, le=2048),
) -> Response:
    if east <= west or north <= south:
        raise HTTPException(status_code=422, detail="Invalid bounding box.")
    try:
        href = await get_visual_href(item_id)
        png = render_visual_cog(href, (west, south, east, north), max_size=max_size)
        return Response(
            content=png,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except PreviewError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
