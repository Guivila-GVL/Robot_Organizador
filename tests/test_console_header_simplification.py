"""Test de validación para la Tarea 80:
Simplificación y reducción del encabezado de la Consola en la barra lateral derecha.
"""
import os
import re
import urllib.request

WORKSPACE_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_RobotOrganizador"
INDEX_HTML = os.path.join(WORKSPACE_DIR, "app", "templates", "index.html")
APP_JS = os.path.join(WORKSPACE_DIR, "app", "static", "js", "app.js")
STYLE_CSS = os.path.join(WORKSPACE_DIR, "app", "static", "css", "style.css")

def test_template_header_simplified():
    print("-> Verificando simplificación en app/templates/index.html...")
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # Verificar que el título ahora es simplemente "Consola"
    assert "<h2>Consola</h2>" in html, "No se encontró <h2>Consola</h2> en index.html"
    assert "<h2>Consola & Actividad</h2>" not in html, "El título anterior 'Consola & Actividad' sigue presente"

    # Verificar que se eliminaron los elementos confusos
    assert "activityLiveBadge" not in html, "El badge 'activityLiveBadge' (Ejecutando/En Vivo) sigue en index.html"
    assert "activityAutoScroll" not in html, "El checkbox 'Auto' sigue en index.html"
    assert "clearActivityTerminal" not in html, "El botón 'Limpiar' sigue en index.html"

    print("   [OK] Título actualizado a 'Consola' y botones innecesarios eliminados")

def test_css_reduced_header():
    print("-> Verificando reducción y compactación en style.css...")
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        css = f.read()

    # Verificar que se redujo el padding de .activity-sidebar-header
    match = re.search(r'\.activity-sidebar-header\s*\{([^}]+)\}', css)
    assert match, "No se encontró .activity-sidebar-header en style.css"
    header_rules = match.group(1)
    assert "padding: 0.65rem" in header_rules or "padding: 0.6rem" in header_rules or "padding: 0.7rem" in header_rules, \
        f"El padding del encabezado no se ha reducido: {header_rules}"

    print("   [OK] Encabezado compactado con padding reducido correctamente")

def test_live_server():
    print("-> Verificando entrega en vivo desde http://127.0.0.1:8002/...")
    req = urllib.request.Request("http://127.0.0.1:8002/")
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200
        content = response.read().decode("utf-8")
        assert "<h2>Consola</h2>" in content
        assert "Consola & Actividad" not in content
        assert "activityLiveBadge" not in content
        assert "activityAutoScroll" not in content

    print("   [OK] El servidor en vivo entrega el encabezado limpio 'Consola'")

if __name__ == "__main__":
    print("==========================================================")
    print("TEST: SIMPLIFICACIÓN Y REDUCCIÓN ENCABEZADO CONSOLA (T80)")
    print("==========================================================")
    test_template_header_simplified()
    test_css_reduced_header()
    test_live_server()
    print("==========================================================")
    print("¡TODAS LAS PRUEBAS DE T80 PASARON EXITOSAMENTE!")
    print("==========================================================")
