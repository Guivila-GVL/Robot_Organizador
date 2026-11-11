"""Test de validación para la Tarea 81:
Simplificación de la sección de actividad / terminal en la barra lateral derecha:
1. Renombrar 'TERMINAL CMD & LOGS' a 'ACTIVIDAD'.
2. Eliminar el filtro confuso 'Todas' / 'Todos'.
3. Disponer únicamente los 3 filtros: 'ESIOS' (sin el icono de la pila), 'Proyecto' y 'Runners'.
4. Actualización dinámica en el filtro 'Proyecto' de los servicios y tareas/runners que están funcionando.
"""
import os
import re
import urllib.request

WORKSPACE_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_RobotOrganizador"
INDEX_HTML = os.path.join(WORKSPACE_DIR, "app", "templates", "index.html")
APP_JS = os.path.join(WORKSPACE_DIR, "app", "static", "js", "app.js")

def test_template_activity_terminal():
    print("-> Verificando index.html para Tarea 81...")
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Título ACTIVIDAD
    assert "<span>ACTIVIDAD</span>" in html, "No se encontró <span>ACTIVIDAD</span> en index.html"
    assert "TERMINAL CMD & LOGS" not in html, "El título anterior 'TERMINAL CMD & LOGS' sigue presente"

    # 2. Filtros simplificados en .console-filter-buttons
    filter_block_match = re.search(r'<div class="console-filter-buttons">(.*?)</div>', html, re.DOTALL)
    assert filter_block_match, "No se encontró .console-filter-buttons en index.html"
    filter_html = filter_block_match.group(1)

    # Verificar que NO está el botón 'Todas' o 'Todos'
    assert 'data-filter="all"' not in filter_html, "El filtro 'Todas' / 'all' sigue presente en los botones de filtro"
    assert "Todas" not in filter_html, "La etiqueta 'Todas' sigue en los botones de filtro"

    # Verificar que ESIOS no tiene el icono de la pila 🔋
    assert "🔋" not in filter_html, "El icono de la pila 🔋 sigue presente en los botones de filtro"
    assert 'data-filter="esios"' in filter_html and ">ESIOS</button>" in filter_html, "Falta el botón limpio ESIOS"

    # Verificar Proyecto y Runners
    assert 'data-filter="project"' in filter_html and ">Proyecto</button>" in filter_html, "Falta el botón Proyecto"
    assert 'data-filter="runner"' in filter_html and ">Runners</button>" in filter_html, "Falta el botón Runners"

    print("   [OK] index.html actualizado con título 'ACTIVIDAD' y filtros limpios (ESIOS, Proyecto, Runners)")

def test_js_project_activity_and_filters():
    print("-> Verificando lógica JS en app.js...")
    with open(APP_JS, "r", encoding="utf-8") as f:
        js = f.read()

    # 1. Filtro por defecto es 'project'
    assert "state.consoleFilter = 'project';" in js, "state.consoleFilter no se inicializa a 'project'"

    # 2. Sincronización dinámica de proyectos funcionando
    assert "statusIndicator" in js, "Falta lógica de statusIndicator para proyectos funcionando en app.js"
    assert "[Ejecutando]" in js or "⚡" in js, "Falta indicador de ejecución activa para proyectos"
    assert "[En línea]" in js or "🟢" in js, "Falta indicador en línea para proyectos"

    # 3. Integración de actividad en ejecución de Runner cuando filter === 'project'
    assert "isRunnerOnThisProj" in js, "Falta detección de Runner activo para el proyecto en renderConsoleTerminal"

    print("   [OK] app.js configurado con seguimiento dinámico de proyectos funcionando y filtro inicial 'project'")

def test_live_server_delivery():
    print("-> Verificando entrega HTTP real en http://127.0.0.1:8002/...")
    req = urllib.request.Request("http://127.0.0.1:8002/")
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200
        content = response.read().decode("utf-8")

        assert "<span>ACTIVIDAD</span>" in content, "El servidor en vivo no sirve <span>ACTIVIDAD</span>"
        assert "TERMINAL CMD & LOGS" not in content, "El servidor en vivo todavía sirve TERMINAL CMD & LOGS"
        
        # Verificar que en los botones de filtro de consola no existe 'all' ni la pila 🔋
        filter_match = re.search(r'<div class="console-filter-buttons">(.*?)</div>', content, re.DOTALL)
        assert filter_match, "No se encontró .console-filter-buttons en el contenido en vivo"
        live_filter_html = filter_match.group(1)
        assert 'data-filter="all"' not in live_filter_html, "El servidor en vivo todavía sirve data-filter='all' en la consola"
        assert "🔋" not in live_filter_html, "El servidor en vivo todavía sirve 🔋 ESIOS con la pila"
        assert ">ESIOS</button>" in live_filter_html, "El servidor en vivo no sirve el botón limpio ESIOS"
        assert ">Proyecto</button>" in live_filter_html, "El servidor en vivo no sirve el botón Proyecto"
        assert ">Runners</button>" in live_filter_html, "El servidor en vivo no sirve el botón Runners"

    print("   [OK] El servidor en vivo entrega la interfaz simplificada y correcta")

if __name__ == "__main__":
    print("==========================================================")
    print("TEST: SIMPLIFICACIÓN ACTIVIDAD Y FILTROS DE PROYECTO (T81)")
    print("==========================================================")
    test_template_activity_terminal()
    test_js_project_activity_and_filters()
    test_live_server_delivery()
    print("==========================================================")
    print("¡TODAS LAS PRUEBAS DE T81 PASARON EXITOSAMENTE!")
    print("==========================================================")
