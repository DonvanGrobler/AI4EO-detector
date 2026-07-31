from __future__ import annotations

from io import BytesIO
from urllib.parse import quote, urlparse

import httpx
import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.errors import RasterioIOError
from rasterio.windows import Window, from_bounds
from rasterio.warp import transform_bounds

from app.services.earth_search import COLLECTION, EARTH_SEARCH_BASE

ALLOWED_ASSET_HOST_SUFFIXES = (
    ".amazonaws.com",
    ".aws.element84.com",
    ".s3.amazonaws.com",
)


class PreviewError(RuntimeError):
    pass


def _validate_asset_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise PreviewError("The STAC visual asset is not a permitted HTTPS URL.")
    if not any(parsed.hostname.endswith(suffix) for suffix in ALLOWED_ASSET_HOST_SUFFIXES):
        raise PreviewError("The STAC visual asset host is not permitted.")


async def get_visual_href(item_id: str) -> str:
    encoded_id = quote(item_id, safe="")
    item_url = f"{EARTH_SEARCH_BASE}/collections/{COLLECTION}/items/{encoded_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(item_url, headers={"User-Agent": "EO-Image-Check-MVP/0.1"})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise PreviewError(f"Could not retrieve STAC item: {exc}") from exc
    href = response.json().get("assets", {}).get("visual", {}).get("href")
    if not href:
        raise PreviewError("This STAC item does not contain a visual asset.")
    _validate_asset_url(href)
    return href


def _safe_window(src: rasterio.io.DatasetReader, bbox_wgs84: tuple[float, float, float, float]) -> Window:
    dataset_bounds = transform_bounds("EPSG:4326", src.crs, *bbox_wgs84, densify_pts=21)
    requested = from_bounds(*dataset_bounds, transform=src.transform)
    full = Window(0, 0, src.width, src.height)
    try:
        return requested.intersection(full)
    except Exception as exc:
        raise PreviewError("The selected area does not overlap this Sentinel-2 scene.") from exc


def _output_shape(window: Window, max_size: int = 900) -> tuple[int, int]:
    width = max(1, int(round(window.width)))
    height = max(1, int(round(window.height)))
    scale = min(max_size / width, max_size / height, 1.0)
    return max(1, int(height * scale)), max(1, int(width * scale))


def render_visual_cog(
    href: str,
    bbox_wgs84: tuple[float, float, float, float],
    max_size: int = 900,
) -> bytes:
    _validate_asset_url(href)
    env_options = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff,.TIF,.TIFF",
        "GDAL_HTTP_MULTIRANGE": "YES",
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
        "AWS_NO_SIGN_REQUEST": "YES",
    }
    try:
        with rasterio.Env(**env_options), rasterio.open(href) as src:
            window = _safe_window(src, bbox_wgs84)
            out_height, out_width = _output_shape(window, max_size=max_size)
            indexes = [1, 2, 3] if src.count >= 3 else [1]
            data = src.read(
                indexes,
                window=window,
                out_shape=(len(indexes), out_height, out_width),
                resampling=Resampling.bilinear,
                boundless=False,
            )
    except RasterioIOError as exc:
        raise PreviewError(f"Could not stream the public COG asset: {exc}") from exc

    if data.shape[0] == 1:
        data = np.repeat(data, 3, axis=0)
    rgb = np.moveaxis(data[:3], 0, -1)
    if rgb.dtype != np.uint8:
        low, high = np.nanpercentile(rgb, (2, 98))
        if high <= low:
            high = low + 1
        rgb = np.clip((rgb - low) / (high - low) * 255, 0, 255).astype(np.uint8)

    image = Image.fromarray(rgb, mode="RGB")
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
