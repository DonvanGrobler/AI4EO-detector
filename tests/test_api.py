from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_without_analytics_token(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_WEB_ANALYTICS_TOKEN", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.5.1",
        "analytics_configured": False,
        "analytics_status": "missing",
    }


def test_health_with_valid_analytics_token(monkeypatch):
    monkeypatch.setenv(
        "CLOUDFLARE_WEB_ANALYTICS_TOKEN",
        "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    )
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["analytics_configured"] is True
    assert response.json()["analytics_status"] == "configured"


def test_health_reports_invalid_analytics_token_without_exposing_it(monkeypatch):
    token = "bad-token'><script>"
    monkeypatch.setenv("CLOUDFLARE_WEB_ANALYTICS_TOKEN", token)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["analytics_configured"] is False
    assert response.json()["analytics_status"] == "invalid_format"
    assert token not in response.text


def test_index_omits_analytics_beacon_without_token(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_WEB_ANALYTICS_TOKEN", raising=False)
    response = client.get("/")
    assert response.status_code == 200
    assert "cloudflare-web-analytics" not in response.text
    assert "static.cloudflareinsights.com/beacon.min.js" not in response.text


def test_index_injects_analytics_beacon_with_valid_token(monkeypatch):
    token = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    monkeypatch.setenv("CLOUDFLARE_WEB_ANALYTICS_TOKEN", token)
    response = client.get("/")
    assert response.status_code == 200
    assert "cloudflare-web-analytics" not in response.text
    assert "static.cloudflareinsights.com/beacon.min.js" in response.text
    assert token in response.text


def test_index_rejects_malformed_analytics_token(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_WEB_ANALYTICS_TOKEN", "bad-token'><script>")
    response = client.get("/")
    assert response.status_code == 200
    assert "static.cloudflareinsights.com/beacon.min.js" not in response.text


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
