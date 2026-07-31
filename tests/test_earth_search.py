from datetime import date

from app.models import SearchRequest
from app.services.earth_search import (
    SearchPeriod,
    _diagnostics,
    bbox_from_point,
    build_periods,
    build_stac_payload,
    choose_best_feature,
)


def feature(item_id: str, day: str, cloud: float, west: float = 0, east: float = 1):
    return {
        "id": item_id,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[west, 0], [east, 0], [east, 1], [west, 1], [west, 0]]],
        },
        "properties": {"datetime": f"{day}T10:00:00Z", "eo:cloud_cover": cloud},
        "assets": {"visual": {"href": f"https://example.amazonaws.com/{item_id}.tif"}},
    }


def test_bbox_has_expected_order_and_size():
    bbox = bbox_from_point(47.27, 11.39, 5)
    assert bbox[0] < 11.39 < bbox[2]
    assert bbox[1] < 47.27 < bbox[3]


def test_claimed_periods_do_not_overlap_event_boundaries():
    request = SearchRequest(
        latitude=47.27,
        longitude=11.39,
        date_mode="claimed_period",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
        window_days=30,
    )
    periods = build_periods(request)
    assert periods[0].end == date(2026, 7, 19)
    assert periods[1].start == date(2026, 7, 20)
    assert periods[2].start == date(2026, 7, 23)


def test_latest_mode_builds_one_backwards_search():
    request = SearchRequest(
        latitude=47.27,
        longitude=11.39,
        date_mode="latest_available",
        reference_date=date(2026, 7, 31),
        window_days=90,
    )
    periods = build_periods(request)
    assert len(periods) == 1
    assert periods[0].name == "latest"
    assert periods[0].end == date(2026, 7, 31)
    assert periods[0].start == date(2026, 5, 2)


def test_payload_keeps_cloudy_scenes_for_diagnostics():
    payload = build_stac_payload(
        [10, 40, 11, 41],
        SearchPeriod("during", date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 1)),
    )
    assert payload["collections"] == ["sentinel-2-c1-l2a"]
    assert "query" not in payload
    assert payload["limit"] == 100


def test_scene_scoring_prefers_full_coverage():
    bbox = [0, 0, 1, 1]
    features = [
        feature("partial-clear", "2026-07-20", 0, west=0, east=0.5),
        feature("full-cloudier", "2026-07-20", 20),
    ]
    selected, coverage = choose_best_feature(features, bbox, date(2026, 7, 20), cloud_cover=30)
    assert selected["id"] == "full-cloudier"
    assert coverage == 1


def test_latest_selection_prefers_newest_scene_within_threshold():
    bbox = [0, 0, 1, 1]
    features = [
        feature("older-clear", "2026-07-20", 2),
        feature("newer-acceptable", "2026-07-25", 25),
        feature("newest-cloudy", "2026-07-30", 80),
    ]
    selected, _ = choose_best_feature(
        features,
        bbox,
        date(2026, 7, 31),
        cloud_cover=30,
        selection_mode="latest",
    )
    assert selected["id"] == "newer-acceptable"


def test_diagnostics_explain_newer_cloudy_scene():
    bbox = [0, 0, 1, 1]
    selected = feature("selected", "2026-07-25", 10)
    newer_cloudy = feature("newer-cloudy", "2026-07-30", 75)
    period = SearchPeriod(
        "latest",
        date(2026, 5, 1),
        date(2026, 7, 31),
        date(2026, 7, 31),
        "latest",
    )
    diagnostics = _diagnostics([selected, newer_cloudy], selected, bbox, period, 30)
    assert diagnostics["closer_or_newer_cloudy_count"] == 1
    assert "newer acquisition" in diagnostics["recency_explanation"]
    assert diagnostics["closest_or_newest_cloud_cover"] == 75
