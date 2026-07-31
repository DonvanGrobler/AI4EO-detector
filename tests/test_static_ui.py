from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_leaflet_stylesheet_uses_official_194_integrity_hash():
    html = (ROOT / "app/static/index.html").read_text()
    assert "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" in html


def test_v04_assets_and_guided_workflow_are_loaded():
    html = (ROOT / "app/static/index.html").read_text()
    assert '/static/styles-v04.css' in html
    assert '/static/js/ui-v04.js' in html
    assert 'id="theme-toggle"' in html
    assert 'id="search-loading"' in html
    assert 'id="results-layout"' in html
    assert 'id="viewer-loading"' in html
    assert 'id="open-gemini"' in html


def test_future_step_tabs_begin_disabled_and_no_mvp_badge_is_shown():
    html = (ROOT / "app/static/index.html").read_text()
    assert 'data-step="2" disabled' in html
    assert 'data-step="3" disabled' in html
    assert 'data-step="4" disabled' in html
    assert 'status-pill' not in html


def test_compact_map_viewer_loading_and_dark_mode_styles_are_present():
    compact_css = (ROOT / "app/static/styles-v03.css").read_text()
    ui_css = (ROOT / "app/static/styles-v04.css").read_text()
    assert '#step-3 #map { height: 390px; min-height: 390px; }' in compact_css
    assert 'html[data-theme="dark"]' in ui_css
    assert '.results-layout.single-result' in ui_css
    assert '.viewer-loading' in ui_css


def test_v04_javascript_contains_navigation_and_loading_states():
    js = (ROOT / "app/static/js/ui-v04.js").read_text()
    assert 'function updateStepTabs' in js
    assert 'function resetHandoffFlow' in js
    assert 'Preparing preview…' in js
    assert 'runSearchV04' in js
