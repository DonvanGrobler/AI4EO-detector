from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_leaflet_stylesheet_uses_official_194_integrity_hash():
    html = (ROOT / "app/static/index.html").read_text()
    assert "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" in html


def test_image_viewer_handlers_are_registered_once():
    js = (ROOT / "app/static/app.js").read_text()
    assert js.count('byId("viewer-zoom-in").addEventListener') == 1
    assert js.count('byId("viewer-close").addEventListener') == 1


def test_step_three_map_is_compact_and_viewer_is_present():
    html = (ROOT / "app/static/index.html").read_text()
    css = (ROOT / "app/static/styles.css").read_text()
    assert 'id="image-viewer"' in html
    assert '#step-3 #map { height: 390px; min-height: 390px; }' in css
