from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_claimed_search_rejects_invalid_dates_before_network_call():
    response = client.post(
        "/api/search",
        json={
            "latitude": 47.27,
            "longitude": 11.39,
            "date_mode": "claimed_period",
            "start_date": "2026-07-22",
            "end_date": "2026-07-20",
            "radius_km": 5,
            "cloud_cover": 30,
            "window_days": 30,
        },
    )
    assert response.status_code == 422


def test_claimed_search_requires_a_date_before_network_call():
    response = client.post(
        "/api/search",
        json={
            "latitude": 47.27,
            "longitude": 11.39,
            "date_mode": "claimed_period",
        },
    )
    assert response.status_code == 422


def test_preview_rejects_invalid_bbox():
    response = client.get("/api/preview/example.png?west=10&south=40&east=9&north=41")
    assert response.status_code == 422


def test_preview_rejects_oversized_output():
    response = client.get(
        "/api/preview/example.png?west=9&south=40&east=10&north=41&max_size=4096"
    )
    assert response.status_code == 422
