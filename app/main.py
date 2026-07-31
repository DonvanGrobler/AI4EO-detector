from __future__ import annotations

import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.models import SearchRequest, SearchResponse
from app.services.earth_search import EarthSearchError, search_sentinel2
from app.services.preview import PreviewError, get_visual_href, render_visual_cog

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ANALYTICS_MARKER = "<!-- cloudflare-web-analytics -->"
ANALYTICS_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
APP_VERSION = "0.5.1"

app = FastAPI(
    title="EO Image Check",
    description="Check Google AI provenance and independently compare broad geospatial claims with public Sentinel-2 observations.",
    version=APP_VERSION,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def analytics_token_status() -> tuple[bool, str]:
    """Return safe analytics configuration status without exposing the token."""
    token = os.getenv("CLOUDFLARE_WEB_ANALYTICS_TOKEN", "").strip()
    if not token:
        return False, "missing"
    if not ANALYTICS_TOKEN_PATTERN.fullmatch(token):
        return False, "invalid_format"
    return True, "configured"


def cloudflare_analytics_script() -> str:
    """Return the Cloudflare beacon only when a valid deployment token is set."""
    configured, _ = analytics_token_status()
    if not configured:
        return ""

    token = os.environ["CLOUDFLARE_WEB_ANALYTICS_TOKEN"].strip()
    beacon_config = json.dumps({"token": token}, separators=(",", ":"))
    return (
        '<script type="module" '
        'src="https://static.cloudflareinsights.com/beacon.min.js" '
        f"data-cf-beacon='{beacon_config}'></script>"
    )


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    page = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    page = page.replace(ANALYTICS_MARKER, cloudflare_analytics_script())
    return HTMLResponse(page, headers={"Cache-Control": "no-cache"})


@app.get("/health")
async def health() -> dict[str, str | bool]:
    analytics_configured, analytics_status = analytics_token_status()
    return {
        "status": "ok",
        "version": APP_VERSION,
        "analytics_configured": analytics_configured,
        "analytics_status": analytics_status,
    }


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
