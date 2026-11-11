import sys
import os
import re
import urllib.request

WORKSPACE_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_RobotOrganizador"
INDEX_HTML = os.path.join(WORKSPACE_DIR, "app", "templates", "index.html")
APP_JS = os.path.join(WORKSPACE_DIR, "app", "static", "js", "app.js")
STYLE_CSS = os.path.join(WORKSPACE_DIR, "app", "static", "css", "style.css")

def test_template_structure():
    print("-> Verificando estructura de app/templates/index.html...")
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Cabecera superior: NO debe contener btnHeaderRunQueue ni btnHeaderPauseQueue ni btnOpenGlobalQueue
    top_nav = re.search(r'<header class="top-nav">.*?</header>', html, re.DOTALL)
    assert top_nav, "No se encontró <header class=\"top-nav\">"
    top_nav_content = top_nav.group(0)
    assert "btnHeaderRunQueue" not in top_nav_content, "btnHeaderRunQueue todavía está en la cabecera"
    assert "btnHeaderPauseQueue" not in top_nav_content, "btnHeaderPauseQueue todavía está en la cabecera"
    assert "btnOpenGlobalQueue" not in top_nav_content, "btnOpenGlobalQueue todavía está en la cabecera"
    print("   [OK] Botones de cola eliminados de la cabecera superior")

    # 2. Barra de tareas de cada proyecto: NO debe contener queueBanner
    task_toolbar = re.search(r'<section class="task-toolbar">.*?</section>', html, re.DOTALL)
    assert task_toolbar, "No se encontró <section class=\"task-toolbar\">"
    task_toolbar_content = task_toolbar.group(0)
    assert "queueBanner" not in task_toolbar_content, "queueBanner todavía está en task-toolbar de los proyectos"
    assert "btnBannerRunQueue" not in task_toolbar_content, "btnBannerRunQueue todavía está en task-toolbar"
    assert "btnBannerPauseQueue" not in task_toolbar_content, "btnBannerPauseQueue todavía está en task-toolbar"
    print("   [OK] Banner de cola y botones eliminados del toolbar de proyectos")

    # 3. Columna lateral derecha (Consola & Actividad): DEBE contener globalQueuePanel en la parte superior
    assert "globalQueuePanel" in html, "Falta globalQueuePanel en index.html"
    assert "btnSidebarRunQueue" in html, "Falta btnSidebarRunQueue en globalQueuePanel"
    assert "btnSidebarPauseQueue" in html, "Falta btnSidebarPauseQueue en globalQueuePanel"
    assert "btnSidebarQueueModal" in html, "Falta btnSidebarQueueModal en globalQueuePanel"
    assert "btnSidebarCopyQueue" in html, "Falta btnSidebarCopyQueue en globalQueuePanel"
    assert "queueLiveDetail" in html, "Falta queueLiveDetail para seguimiento detallado"
    print("   [OK] Panel de Cola Global con botones y seguimiento detallado ubicado en columna derecha")

def test_js_logic():
    print("-> Verificando app/static/js/app.js...")
    with open(APP_JS, "r", encoding="utf-8") as f:
        js = f.read()

    assert "function renderGlobalQueueLiveDetail" in js, "Falta función renderGlobalQueueLiveDetail en app.js"
    assert "btnSidebarRunQueue" in js, "Falta referencia a btnSidebarRunQueue en app.js"
    assert "btnSidebarPauseQueue" in js, "Falta referencia a btnSidebarPauseQueue en app.js"
    assert "globalQueueCount" in js, "Falta actualización de globalQueueCount en app.js"
    assert "renderGlobalQueueLiveDetail(" in js, "Falta llamada a renderGlobalQueueLiveDetail"
    print("   [OK] Lógica JS implementada correctamente para la cola lateral y seguimiento en vivo")

def test_css_styles():
    print("-> Verificando app/static/css/style.css...")
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        css = f.read()

    assert ".global-queue-panel" in css, "Falta .global-queue-panel en style.css"
    assert ".queue-panel-buttons" in css, "Falta .queue-panel-buttons en style.css"
    assert ".queue-live-detail" in css, "Falta .queue-live-detail en style.css"
    assert ".queue-live-step-box" in css, "Falta .queue-live-step-box en style.css"
    assert ".queue-live-progress-row" in css, "Falta .queue-live-progress-row en style.css"
    print("   [OK] Estilos CSS verificados para el panel y tarjetas en vivo")

def test_live_server_http():
    print("-> Verificando respuesta real del servidor FastAPI en http://127.0.0.1:8002/...")
    req = urllib.request.Request("http://127.0.0.1:8002/")
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200, f"Status code no es 200: {response.status}"
        body = response.read().decode("utf-8")
        assert "globalQueuePanel" in body, "globalQueuePanel no se sirvió en el HTML"
        assert "btnSidebarRunQueue" in body, "btnSidebarRunQueue no se sirvió en el HTML"
        assert "btnSidebarPauseQueue" in body, "btnSidebarPauseQueue no se sirvió en el HTML"
        assert "btnSidebarQueueModal" in body, "btnSidebarQueueModal no se sirvió en el HTML"
        assert "btnSidebarCopyQueue" in body, "btnSidebarCopyQueue no se sirvió en el HTML"
        assert "queueLiveDetail" in body, "queueLiveDetail no se sirvió en el HTML"
        # Comprobar que en header no están los botones viejos
        top_nav_match = re.search(r'<header class="top-nav">.*?</header>', body, re.DOTALL)
        assert top_nav_match, "No se encontró top-nav en HTML servido"
        assert "btnHeaderRunQueue" not in top_nav_match.group(0), "btnHeaderRunQueue todavía está en header servido"
        print("   [OK] Servidor responde 200 OK y entrega la nueva interfaz correctamente")

if __name__ == "__main__":
    print("==========================================================")
    print("TEST: REORGANIZACIÓN DE COLA GLOBAL EN COLUMNA DERECHA (T72)")
    print("==========================================================")
    test_template_structure()
    test_js_logic()
    test_css_styles()
    test_live_server_http()
    print("==========================================================")
    print("¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
    print("==========================================================")
