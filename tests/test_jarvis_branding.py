import os
import json
import urllib.request
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE_DIR, "app", "templates", "index.html")
STYLE_PATH = os.path.join(BASE_DIR, "app", "static", "css", "style.css")
MANIFEST_PATH = os.path.join(BASE_DIR, "app", "static", "manifest.json")
FAVICON_PATH = os.path.join(BASE_DIR, "app", "static", "favicon.svg")


def test_index_html_branding():
    assert os.path.exists(INDEX_PATH), "index.html does not exist"
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "<title>JARVIS · Sistema de Gestión de Proyectos</title>" in content
    assert 'content="JARVIS"' in content
    assert 'href="/static/favicon.svg"' in content
    assert "jarvis-logo-icon" in content
    assert "jarvis-core-svg" in content
    assert "<h1>JARVIS</h1>" in content
    assert "brand-ai-badge" in content
    assert "Gestión Inteligente de Proyectos" in content
    assert "⚡ JARVIS · Puerto :8002" in content
    print("test_index_html_branding: PASSED")


def test_style_css_rules():
    assert os.path.exists(STYLE_PATH), "style.css does not exist"
    with open(STYLE_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    assert ".jarvis-logo-icon" in css
    assert ".jarvis-core-svg" in css
    assert ".brand-title-row" in css
    assert ".brand-ai-badge" in css
    print("test_style_css_rules: PASSED")


def test_manifest_json():
    assert os.path.exists(MANIFEST_PATH), "manifest.json does not exist"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("short_name") == "JARVIS"
    assert "JARVIS" in data.get("name", "")
    print("test_manifest_json: PASSED")


def test_favicon_svg_validity():
    assert os.path.exists(FAVICON_PATH), "favicon.svg does not exist"
    tree = ET.parse(FAVICON_PATH)
    root = tree.getroot()
    assert "svg" in root.tag.lower()
    print("test_favicon_svg_validity: PASSED")


def test_live_server_endpoints():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8002/") as resp:
            assert resp.getcode() == 200
            html = resp.read().decode("utf-8")
            assert "JARVIS" in html
            print("test_live_server_endpoints (root): PASSED")

        with urllib.request.urlopen("http://127.0.0.1:8002/static/favicon.svg") as resp:
            assert resp.getcode() == 200
            svg_content = resp.read().decode("utf-8")
            assert "<svg" in svg_content
            print("test_live_server_endpoints (favicon.svg): PASSED")

        with urllib.request.urlopen("http://127.0.0.1:8002/static/manifest.json") as resp:
            assert resp.getcode() == 200
            m_data = json.loads(resp.read().decode("utf-8"))
            assert m_data.get("short_name") == "JARVIS"
            print("test_live_server_endpoints (manifest.json): PASSED")
    except Exception as e:
        print(f"Server check failed: {e}")
        raise


if __name__ == "__main__":
    test_index_html_branding()
    test_style_css_rules()
    test_manifest_json()
    test_favicon_svg_validity()
    test_live_server_endpoints()
    print("\nALL BRANDING TESTS PASSED!")
