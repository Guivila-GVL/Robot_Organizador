import urllib.request

def test_ui():
    html = urllib.request.urlopen('http://127.0.0.1:8002/').read().decode('utf-8')
    js = urllib.request.urlopen('http://127.0.0.1:8002/static/js/app.js').read().decode('utf-8')

    header_html = html[:html.find('</header>')]
    
    assert "openProjectResource('onenote')" not in header_html, "OneNote should be removed from header"
    assert "openProjectResource('skills')" not in header_html, "Skills should be removed from header"
    print("✓ OneNote and Skills removed from top bar")

    assert "<h2>Consola</h2>" in html, "Sidebar header should be simply Consola"
    assert "Consola · Robot de Gestión" not in html, "Consola · Robot de Gestión should not exist"
    print("✓ Consola header title verified")

    assert '<span class="tab-icon">🚀</span> Tareas' in html, "Tab should be named Tareas"
    assert '<span class="tab-icon">🔋</span> ESIOS' in html, "Tab should be named ESIOS"
    print("✓ Tab labels (Tareas and ESIOS) verified")

    assert 'esiosStatusChip' not in html, "esiosStatusChip should be removed"
    assert '✅ Listo' not in html, "Listo check should be removed"
    print("✓ Listo check chip removed")

    assert 'btnQuickOpenEsios' not in html, "btnQuickOpenEsios should be removed from global queue"
    print("✓ Ir a ESIOS from global queue removed")

    # Inside esios panel in app.js, the button to switch back to queue shouldn't exist
    assert "onclick=\"setSidebarTopTab('queue')\"" not in js, "Back button to queue in ESIOS card should be removed"
    print("✓ Button back to queue inside ESIOS removed from app.js")

    print("\nALL 6 CHECKS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_ui()
