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

    # 1. Selector de pestañas superiores
    assert "sidebarTopTabs" in html, "Falta #sidebarTopTabs en index.html"
    assert "tabBtnQueue" in html, "Falta #tabBtnQueue en index.html"
    assert "btnTrackEsios" in html, "Falta #btnTrackEsios en index.html"
    assert "esiosStatusChip" in html, "Falta #esiosStatusChip en index.html"
    print("   [OK] Pestañas superiores (Cola Global / Seguimiento ESIOS) presentes en la barra lateral")

    # 2. Panel A: Cola Global intacto
    assert "globalQueuePanel" in html, "Falta #globalQueuePanel en index.html"
    assert "btnSidebarRunQueue" in html, "Falta #btnSidebarRunQueue en index.html"
    assert "btnSidebarPauseQueue" in html, "Falta #btnSidebarPauseQueue en index.html"
    assert "btnSidebarQueueModal" in html, "Falta #btnSidebarQueueModal en index.html"
    assert "btnSidebarCopyQueue" in html, "Falta #btnSidebarCopyQueue en index.html"
    assert "btnQuickOpenEsios" in html, "Falta botón de acceso rápido #btnQuickOpenEsios en la cola"
    assert "queueLiveDetail" in html, "Falta #queueLiveDetail en index.html"
    print("   [OK] Panel de Cola Global con botones y detalle en vivo presente")

    # 3. Panel B: Pestaña Superior de Seguimiento ESIOS
    assert "esiosTrackingPanel" in html, "Falta #esiosTrackingPanel en index.html"
    assert "btnEsiosQuickSync" in html, "Falta #btnEsiosQuickSync en index.html"
    assert "sidebarProgressArea" in html, "Falta #sidebarProgressArea para contenido dinámico ESIOS"
    print("   [OK] Pestaña superior de Seguimiento ESIOS configurada correctamente")

    # 4. Eliminación de redundancia de proyecto
    activity_sidebar_match = re.search(r'<aside class="sidebar-right activity-sidebar".*?</aside>', html, re.DOTALL)
    assert activity_sidebar_match, "No se encontró <aside class=\"sidebar-right activity-sidebar\">"
    sidebar_content = activity_sidebar_match.group(0)

    assert "btnTrackProject" not in sidebar_content, "btnTrackProject todavía está presente en la barra lateral"
    assert "sidebarProjectSelect" not in sidebar_content, "sidebarProjectSelect todavía está presente en la barra lateral"
    assert "sidebarProjName" not in sidebar_content, "sidebarProjName todavía está presente en la barra lateral"
    assert "selected-project-banner-mini" not in sidebar_content, "selected-project-banner-mini todavía está presente"
    print("   [OK] Tarjeta y selector redundante de Proyecto eliminados de la barra lateral derecha")

def test_js_logic():
    print("-> Verificando lógica JS en app/static/js/app.js...")
    with open(APP_JS, "r", encoding="utf-8") as f:
        js = f.read()

    assert "function setSidebarTopTab(tab)" in js, "Falta setSidebarTopTab(tab) en app.js"
    assert "window.setSidebarTopTab = setSidebarTopTab" in js, "setSidebarTopTab no está expuesta en window"
    assert "function setTrackingMode(mode)" in js, "Falta función compatible setTrackingMode en app.js"
    assert "esiosStatusChip" in js, "Falta lógica para actualizar esiosStatusChip en app.js"
    assert "esiosTrackingPanel" in js, "Falta referencia a esiosTrackingPanel en app.js"
    print("   [OK] Funciones JS de control de pestañas superiores e integración ESIOS implementadas")

def test_css_styles():
    print("-> Verificando estilos en app/static/css/style.css...")
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        css = f.read()

    assert ".sidebar-top-tabs" in css, "Falta .sidebar-top-tabs en style.css"
    assert ".sidebar-top-tab" in css, "Falta .sidebar-top-tab en style.css"
    assert ".sidebar-top-tab.active" in css, "Falta .sidebar-top-tab.active en style.css"
    assert ".esios-status-chip" in css, "Falta .esios-status-chip en style.css"
    assert ".esios-tracking-panel" in css, "Falta .esios-tracking-panel en style.css"
    assert ".btn-open-esios" in css, "Falta .btn-open-esios en style.css"
    print("   [OK] Estilos CSS verificados para las pestañas superiores y panel de ESIOS")

def test_live_server_http():
    print("-> Verificando respuesta real del servidor FastAPI en http://127.0.0.1:8002/...")
    req = urllib.request.Request("http://127.0.0.1:8002/")
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200, f"Status code no es 200: {response.status}"
        body = response.read().decode("utf-8")

        assert "sidebarTopTabs" in body, "sidebarTopTabs no se sirvió en el HTML"
        assert "tabBtnQueue" in body, "tabBtnQueue no se sirvió en el HTML"
        assert "btnTrackEsios" in body, "btnTrackEsios no se sirvió en el HTML"
        assert "esiosTrackingPanel" in body, "esiosTrackingPanel no se sirvió en el HTML"
        assert "btnEsiosQuickSync" in body, "btnEsiosQuickSync no se sirvió en el HTML"
        assert "btnTrackProject" not in body, "btnTrackProject todavía se está sirviendo en el HTML"
        assert "sidebarProjectSelect" not in body, "sidebarProjectSelect todavía se está sirviendo en el HTML"
        print("   [OK] Servidor FastAPI entrega la nueva interfaz con pestañas superiores y sin redundancia")

if __name__ == "__main__":
    print("==========================================================")
    print("TEST: PESTAÑA SUPERIOR ESIOS Y CONSOLA DE ACTIVIDAD (T74)")
    print("==========================================================")
    test_template_structure()
    test_js_logic()
    test_css_styles()
    test_live_server_http()
    print("==========================================================")
    print("¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
    print("==========================================================")
