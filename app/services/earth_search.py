from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal
from urllib.parse import quote

import httpx
from shapely.geometry import box, shape

from app.models import PeriodResult, SceneResult, SearchRequest, SearchResponse

EARTH_SEARCH_BASE = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-c1-l2a"


class EarthSearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchPeriod:
    name: Literal["before", "during", "after", "latest"]
    start: date
    end: date
    target: date
    selection_mode: Literal["closest", "latest"] = "closest"


def bbox_from_point(latitude: float, longitude: float, radius_km: float) -> list[float]:
    """Approximate a square WGS84 bbox around a point."""
    lat_delta = radius_km / 110.574
    cos_lat = max(math.cos(math.radians(latitude)), 0.01)
    lon_delta = radius_km / (111.320 * cos_lat)
    return [
        max(-180.0, longitude - lon_delta),
        max(-90.0, latitude - lat_delta),
        min(180.0, longitude + lon_delta),
        min(90.0, latitude + lat_delta),
    ]


def build_periods(req: SearchRequest) -> list[SearchPeriod]:
    if req.date_mode == "latest_available":
        reference = req.reference_date or date.today()
        return [
            SearchPeriod(
                "latest",
                reference - timedelta(days=req.window_days),
                reference,
                reference,
                "latest",
            )
        ]

    assert req.start_date is not None
    assert req.end_date is not None
    before_end = req.start_date - timedelta(days=1)
    after_start = req.end_date + timedelta(days=1)
    midpoint = req.start_date + (req.end_date - req.start_date) / 2
    return [
        SearchPeriod(
            "before",
            req.start_date - timedelta(days=req.window_days),
            before_end,
            before_end,
        ),
        SearchPeriod("during", req.start_date, req.end_date, midpoint),
        SearchPeriod(
            "after",
            after_start,
            req.end_date + timedelta(days=req.window_days),
            after_start,
        ),
    ]


def _stac_datetime(start: date, end: date) -> str:
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end, time.max, tzinfo=timezone.utc)
    return f"{start_dt.isoformat().replace('+00:00', 'Z')}/{end_dt.isoformat().replace('+00:00', 'Z')}"


def build_stac_payload(bbox: list[float], period: SearchPeriod) -> dict[str, Any]:
    # Cloud filtering is performed locally. Keeping cloudy observations in the
    # response lets the app explain why a temporally closer scene was rejected.
    return {
        "collections": [COLLECTION],
        "bbox": bbox,
        "datetime": _stac_datetime(period.start, period.end),
        "limit": 100,
    }


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _feature_datetime(feature: dict[str, Any]) -> datetime | None:
    properties = feature.get("properties", {})
    value = properties.get("datetime") or properties.get("start_datetime")
    if not value:
        return None
    try:
        return _parse_datetime(value)
    except (TypeError, ValueError):
        return None


def _feature_cloud(feature: dict[str, Any]) -> float | None:
    value = feature.get("properties", {}).get("eo:cloud_cover")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coverage_fraction(feature: dict[str, Any], bbox: list[float]) -> float:
    try:
        aoi = box(*bbox)
        footprint = shape(feature["geometry"])
        if aoi.area <= 0:
            return 0.0
        return max(0.0, min(1.0, footprint.intersection(aoi).area / aoi.area))
    except Exception:
        return 0.0


def _candidate_features(features: list[dict[str, Any]], bbox: list[float]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for feature in features:
        if "visual" not in feature.get("assets", {}):
            continue
        if _feature_datetime(feature) is None:
            continue
        if _coverage_fraction(feature, bbox) <= 0:
            continue
        candidates.append(feature)
    return candidates


def _selection_key(
    feature: dict[str, Any],
    bbox: list[float],
    target: date,
    selection_mode: Literal["closest", "latest"],
) -> tuple[float, float, float]:
    coverage = _coverage_fraction(feature, bbox)
    cloud = _feature_cloud(feature)
    dt_value = _feature_datetime(feature)
    assert dt_value is not None

    # Complete AOI coverage remains the first priority. Within similarly
    # covering scenes, select the closest date or the newest date, then lower cloud.
    coverage_penalty = (1 - coverage) * 1000
    cloud_value = cloud if cloud is not None else 101.0
    if selection_mode == "latest":
        temporal_value = -dt_value.timestamp()
    else:
        temporal_value = abs((dt_value.date() - target).days)
    return coverage_penalty, temporal_value, cloud_value


def choose_best_feature(
    features: list[dict[str, Any]],
    bbox: list[float],
    target: date,
    cloud_cover: float = 100,
    selection_mode: Literal["closest", "latest"] = "closest",
) -> tuple[dict[str, Any], float] | None:
    acceptable = [
        feature
        for feature in _candidate_features(features, bbox)
        if (_feature_cloud(feature) is not None and _feature_cloud(feature) <= cloud_cover)
    ]
    if not acceptable:
        return None
    acceptable.sort(key=lambda feature: _selection_key(feature, bbox, target, selection_mode))
    selected = acceptable[0]
    return selected, _coverage_fraction(selected, bbox)


def _is_temporally_more_relevant(
    feature: dict[str, Any],
    selected: dict[str, Any],
    target: date,
    selection_mode: Literal["closest", "latest"],
) -> bool:
    feature_dt = _feature_datetime(feature)
    selected_dt = _feature_datetime(selected)
    if feature_dt is None or selected_dt is None:
        return False
    if selection_mode == "latest":
        return feature_dt > selected_dt
    return abs((feature_dt.date() - target).days) < abs((selected_dt.date() - target).days)


def _best_cloudy_feature(
    features: list[dict[str, Any]],
    bbox: list[float],
    target: date,
    selection_mode: Literal["closest", "latest"],
) -> dict[str, Any] | None:
    cloudy = [feature for feature in features if _feature_cloud(feature) is not None]
    if not cloudy:
        return None
    cloudy.sort(key=lambda feature: _selection_key(feature, bbox, target, selection_mode))
    return cloudy[0]


def _diagnostics(
    all_features: list[dict[str, Any]],
    selected: dict[str, Any] | None,
    bbox: list[float],
    period: SearchPeriod,
    cloud_threshold: float,
) -> dict[str, Any]:
    candidates = _candidate_features(all_features, bbox)
    latest_feature = max(candidates, key=lambda f: _feature_datetime(f) or datetime.min.replace(tzinfo=timezone.utc), default=None)
    latest_datetime = None
    if latest_feature is not None and _feature_datetime(latest_feature) is not None:
        latest_datetime = (_feature_datetime(latest_feature) or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")

    if selected is None:
        cloudy = [
            feature
            for feature in candidates
            if _feature_cloud(feature) is not None and _feature_cloud(feature) > cloud_threshold
        ]
        best_cloudy = _best_cloudy_feature(cloudy, bbox, period.target, period.selection_mode)
        if cloudy and best_cloudy is not None:
            best_dt = _feature_datetime(best_cloudy)
            best_cloud = _feature_cloud(best_cloudy)
            return {
                "message": (
                    f"Observations were found, but none met the {cloud_threshold:.0f}% scene-cloud threshold. "
                    f"The most relevant rejected scene was {best_dt.date().isoformat() if best_dt else 'unknown'} "
                    f"with {best_cloud:.1f}% cloud cover."
                ),
                "recency_explanation": (
                    "Increase the cloud threshold or search window if a cloudier contextual image is still useful."
                ),
                "latest_catalogued_datetime": latest_datetime,
                "closer_or_newer_cloudy_count": len(cloudy),
                "closest_or_newest_cloudy_datetime": best_dt.isoformat().replace("+00:00", "Z") if best_dt else None,
                "closest_or_newest_cloud_cover": best_cloud,
            }
        return {
            "message": "No Sentinel-2 acquisition with a usable visual asset was catalogued for this AOI and search period.",
            "recency_explanation": (
                "A matching overpass may not have occurred in the selected window, the AOI may fall outside the returned scene footprints, "
                "or a recent product may still be processing or cataloguing."
            ),
            "latest_catalogued_datetime": latest_datetime,
            "closer_or_newer_cloudy_count": 0,
            "closest_or_newest_cloudy_datetime": None,
            "closest_or_newest_cloud_cover": None,
        }

    more_relevant = [
        feature
        for feature in candidates
        if _is_temporally_more_relevant(feature, selected, period.target, period.selection_mode)
    ]
    cloudy_more_relevant = [
        feature
        for feature in more_relevant
        if _feature_cloud(feature) is not None and _feature_cloud(feature) > cloud_threshold
    ]
    best_cloudy = _best_cloudy_feature(cloudy_more_relevant, bbox, period.target, period.selection_mode)

    if best_cloudy is not None:
        best_dt = _feature_datetime(best_cloudy)
        best_cloud = _feature_cloud(best_cloudy)
        relation = "newer" if period.selection_mode == "latest" else "temporally closer"
        explanation = (
            f"{len(cloudy_more_relevant)} {relation} acquisition(s) were catalogued, but exceeded the "
            f"{cloud_threshold:.0f}% scene-cloud threshold. The most relevant rejected scene was "
            f"{best_dt.date().isoformat() if best_dt else 'unknown'} with {best_cloud:.1f}% cloud cover."
        )
        return {
            "message": None,
            "recency_explanation": explanation,
            "latest_catalogued_datetime": latest_datetime,
            "closer_or_newer_cloudy_count": len(cloudy_more_relevant),
            "closest_or_newest_cloudy_datetime": best_dt.isoformat().replace("+00:00", "Z") if best_dt else None,
            "closest_or_newest_cloud_cover": best_cloud,
        }

    selected_dt = _feature_datetime(selected)
    if period.selection_mode == "latest":
        explanation = (
            f"No newer acquisition is currently catalogued for this AOI up to {period.end.isoformat()}. "
            "The next intersecting overpass may not yet have occurred, or a newer product may still be processing or cataloguing."
        )
    elif selected_dt and selected_dt.date() == period.target:
        explanation = "An acceptable observation was available on the target date."
    else:
        explanation = "No temporally closer catalogued acquisition in this search period met the AOI and cloud requirements."

    return {
        "message": None,
        "recency_explanation": explanation,
        "latest_catalogued_datetime": latest_datetime,
        "closer_or_newer_cloudy_count": 0,
        "closest_or_newest_cloudy_datetime": None,
        "closest_or_newest_cloud_cover": None,
    }


async def _fetch_search_features(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    url = f"{EARTH_SEARCH_BASE}/search"
    method = "POST"
    body: dict[str, Any] | None = payload
    features: list[dict[str, Any]] = []

    for _ in range(max_pages):
        try:
            if method == "POST":
                response = await client.post(url, json=body)
            else:
                response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EarthSearchError(f"Earth Search request failed: {exc}") from exc

        data = response.json()
        features.extend(data.get("features", []))
        next_link = next((link for link in data.get("links", []) if link.get("rel") == "next"), None)
        if not next_link:
            break
        url = next_link.get("href")
        if not url:
            break
        method = str(next_link.get("method", "GET")).upper()
        body = next_link.get("body") if method == "POST" else None

    return features


async def _search_period(
    client: httpx.AsyncClient,
    bbox: list[float],
    period: SearchPeriod,
    cloud_cover: float,
) -> PeriodResult:
    features = await _fetch_search_features(client, build_stac_payload(bbox, period))
    selected = choose_best_feature(
        features,
        bbox,
        period.target,
        cloud_cover=cloud_cover,
        selection_mode=period.selection_mode,
    )
    selected_feature = selected[0] if selected else None
    diagnostics = _diagnostics(features, selected_feature, bbox, period, cloud_cover)

    base_result = {
        "period": period.name,
        "search_start": period.start.isoformat(),
        "search_end": period.end.isoformat(),
        "target_date": period.target.isoformat(),
        **diagnostics,
    }
    if selected is None:
        return PeriodResult(**base_result)

    feature, coverage = selected
    props = feature.get("properties", {})
    item_id = feature["id"]
    encoded_id = quote(item_id, safe="")
    query = "&".join(
        [
            f"west={bbox[0]}",
            f"south={bbox[1]}",
            f"east={bbox[2]}",
            f"north={bbox[3]}",
        ]
    )
    scene_dt_value = props.get("datetime") or props.get("start_datetime") or "unknown"
    parsed_scene_dt = _feature_datetime(feature)
    distance_days = abs((parsed_scene_dt.date() - period.target).days) if parsed_scene_dt else 0
    if period.selection_mode == "latest":
        selection_reason = (
            f"Most recent catalogued observation within the {period.start.isoformat()} to {period.end.isoformat()} "
            f"lookback that met the {cloud_cover:.0f}% scene-cloud threshold, prioritising AOI coverage."
        )
    else:
        selection_reason = (
            f"Closest acceptable observation to {period.target.isoformat()} within this period, "
            f"using a {cloud_cover:.0f}% scene-cloud threshold and prioritising AOI coverage."
        )

    scene = SceneResult(
        period=period.name,
        item_id=item_id,
        datetime=scene_dt_value,
        cloud_cover=props.get("eo:cloud_cover"),
        platform=props.get("platform"),
        coverage_fraction=coverage,
        item_url=f"{EARTH_SEARCH_BASE}/collections/{COLLECTION}/items/{encoded_id}",
        preview_url=f"/api/preview/{encoded_id}.png?{query}",
        target_date=period.target.isoformat(),
        date_distance_days=distance_days,
        selection_reason=selection_reason,
    )
    return PeriodResult(**base_result, scene=scene)


async def search_sentinel2(req: SearchRequest) -> SearchResponse:
    bbox = bbox_from_point(req.latitude, req.longitude, req.radius_km)
    periods = build_periods(req)
    timeout = httpx.Timeout(30.0, connect=10.0)
    headers = {"User-Agent": "EO-Image-Check-MVP/0.2"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        results = []
        for period in periods:
            results.append(await _search_period(client, bbox, period, req.cloud_cover))

    reference = req.reference_date if req.date_mode == "latest_available" else req.end_date
    assert reference is not None
    return SearchResponse(
        collection=COLLECTION,
        date_mode=req.date_mode,
        reference_date=reference.isoformat(),
        bbox=bbox,
        cloud_threshold=req.cloud_cover,
        resolution_notice=(
            "Sentinel-2 provides independent 10 m evidence for broad events and landscape changes. "
            "It cannot authenticate fine details in a very-high-resolution screenshot."
        ),
        cloud_notice=(
            "Cloud cover is the Sentinel-2 scene-level metadata value, not a measurement calculated only over the selected AOI. "
            "Inspect the rendered image before drawing conclusions."
        ),
        periods=results,
    )
