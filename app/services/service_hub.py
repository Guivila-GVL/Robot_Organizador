import os
import sys
import time
import socket
import subprocess
import webbrowser
import logging
import urllib.request
from typing import List, Dict, Any, Optional

logger = logging.getLogger("service_hub")

WORKSPACE_ROOT = r"D:\OneDrive\04_Desarrollo_proyectos"
PYTHON_EXE = sys.executable or "python"

SERVICES_CONFIG = [
    {
        "id": "robot_organizador",
        "name": "Robot de Gestión de Proyectos",
        "description": "Centro de Mando, Tareas e Hitos Multi-Proyecto",
        "host": "127.0.0.1",
        "port": 8002,
        "url": "http://localhost:8002",
        "icon": "🤖",
        "color": "#8b5cf6",
        "cwd": os.path.join(WORKSPACE_ROOT, "2026_Proyecto_RobotOrganizador"),
        "start_cmd": [PYTHON_EXE, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8002"]
    },
    {
        "id": "videostudio",
        "name": "VideoStudio AI",
        "description": "Producción de Vídeos Cortos por Libros & Capítulos",
        "host": "127.0.0.1",
        "port": 8001,
        "url": "http://localhost:8001",
        "icon": "🎬",
        "color": "#ec4899",
        "cwd": os.path.join(WORKSPACE_ROOT, "2026_Proyecto_Videos"),
        "start_cmd": [PYTHON_EXE, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
    },
    {
        "id": "comentarista",
        "name": "Comentarista X",
        "description": "Asistente Editorial para X con IA y Grafana",
        "host": "127.0.0.1",
        "port": 8000,
        "url": "http://localhost:8000",
        "icon": "✍️",
        "color": "#38bdf8",
        "cwd": os.path.join(WORKSPACE_ROOT, "2026_Proyecto_Comentarista"),
        "start_cmd": [PYTHON_EXE, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
    },
    {
        "id": "n8n",
        "name": "n8n Automation",
        "description": "Orquestación de Flujos, Noticias y Webhooks",
        "host": "127.0.0.1",
        "port": 5678,
        "url": "http://localhost:5678",
        "icon": "⚡",
        "color": "#ea580c"
    },
    {
        "id": "grafana",
        "name": "Grafana Dashboards",
        "description": "Series Temporales de Energía y Métricas",
        "host": "127.0.0.1",
        "port": 3000,
        "url": "http://localhost:3000",
        "icon": "📊",
        "color": "#f59e0b"
    },
    {
        "id": "certificado_humano",
        "name": "Certificado Humano",
        "description": "Plataforma de Auditoría Técnica y Verificación",
        "host": "127.0.0.1",
        "port": 3001,
        "url": "https://human-certified.vercel.app/",
        "icon": "🏅",
        "color": "#10b981"
    }
]

def check_port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_service_online(service: Dict[str, Any]) -> bool:
    port = service.get("port")
    if port and port != 3001:
        return check_port_open(service.get("host", "127.0.0.1"), port)
    
    if service.get("id") == "certificado_humano":
        if check_port_open("127.0.0.1", 3001, timeout=0.2):
            return True
        try:
            req = urllib.request.Request("https://human-certified.vercel.app/", headers={"User-Agent": "RobotOrganizador/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as res:
                return res.status == 200
        except Exception:
            return True
            
    return False

def get_services_status() -> List[Dict[str, Any]]:
    results = []
    for s in SERVICES_CONFIG:
        is_online = check_service_online(s)
        item = {k: v for k, v in s.items() if k not in ("start_cmd", "cwd")}
        results.append({
            **item,
            "is_online": is_online,
            "can_autostart": bool(s.get("start_cmd")),
            "status_text": "En línea" if is_online else "Inactivo (Click para iniciar)" if s.get("start_cmd") else "Inactivo",
            "status_badge": "online" if is_online else "offline"
        })
    return results

def start_local_service(service_id: str, wait_ready: bool = True, max_wait: float = 5.0) -> Dict[str, Any]:
    service = next((s for s in SERVICES_CONFIG if s["id"] == service_id), None)
    if not service:
        return {"success": False, "error": f"Servicio '{service_id}' no encontrado"}

    if check_service_online(service):
        return {"success": True, "already_running": True, "url": service["url"], "name": service["name"]}

    start_cmd = service.get("start_cmd")
    cwd = service.get("cwd")
    if not start_cmd or not cwd or not os.path.exists(cwd):
        return {"success": False, "error": f"El servicio '{service['name']}' no tiene comando de auto-arranque local"}

    try:
        # CREATE_NEW_PROCESS_GROUP (0x00000200) | CREATE_NO_WINDOW (0x08000000)
        creation_flags = 0x00000200 | 0x08000000
        subprocess.Popen(
            start_cmd,
            cwd=cwd,
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True
        )
        logger.info(f"Iniciando servicio {service['name']} en {cwd}...")
    except Exception as e:
        logger.error(f"Error al iniciar {service['name']}: {e}")
        return {"success": False, "error": str(e)}

    if wait_ready and service.get("port"):
        deadline = time.time() + max_wait
        while time.time() < deadline:
            if check_port_open(service.get("host", "127.0.0.1"), service["port"], timeout=0.25):
                return {"success": True, "started": True, "url": service["url"], "name": service["name"]}
            time.sleep(0.25)

    return {
        "success": True,
        "started": True,
        "url": service["url"],
        "name": service["name"]
    }

def open_url_in_system_browser(url: str) -> bool:
    try:
        if hasattr(os, "startfile"):
            os.startfile(url)
            return True
    except Exception as e:
        logger.warning(f"os.startfile falló para {url}: {e}")

    try:
        webbrowser.open_new_tab(url)
        return True
    except Exception as e:
        logger.error(f"webbrowser falló para {url}: {e}")
        return False

def open_all_services_in_browser() -> Dict[str, Any]:
    active_services = []
    active_urls = []
    started_now = []

    # 1. Arrancar primero cualquier servicio local que esté apagado (VideoStudio, Comentarista)
    for s in SERVICES_CONFIG:
        if s["id"] == "robot_organizador":
            continue
        if not check_service_online(s) and s.get("start_cmd"):
            res = start_local_service(s["id"], wait_ready=False)
            if res.get("success"):
                started_now.append(s)

    # Si hemos arrancado alguno, esperar hasta 5s a que sus puertos respondan
    if started_now:
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if all(check_service_online(s) for s in started_now):
                break
            time.sleep(0.3)

    # 2. Recopilar todos los servicios activos y abrirlos
    for s in SERVICES_CONFIG:
        if s["id"] == "robot_organizador":
            continue

        is_online = check_service_online(s)
        if is_online or s in started_now:
            active_services.append(s["name"])
            active_urls.append(s["url"])
            open_url_in_system_browser(s["url"])

    return {
        "success": True,
        "opened_services": active_services,
        "urls": active_urls,
        "started_services": [s["name"] for s in started_now],
        "method": "os.startfile + frontend"
    }


def _extract_git_remote_url(project_folder: str) -> str:
    git_config = os.path.join(project_folder, ".git", "config")
    if os.path.exists(git_config):
        try:
            with open(git_config, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            import re
            m = re.search(r"url\s*=\s*(https?://[^\s]+|git@[^\s]+)", content)
            if m:
                raw_url = m.group(1).strip()
                if raw_url.startswith("git@github.com:"):
                    raw_url = "https://github.com/" + raw_url.split("git@github.com:", 1)[1]
                if raw_url.endswith(".git"):
                    raw_url = raw_url[:-4]
                return raw_url
        except Exception:
            pass
    return "https://github.com/Guivila-GVL?tab=repositories"


def open_project_resource(project_id: str, resource_key: str) -> Dict[str, Any]:
    from app.database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()

    if not project:
        conn.close()
        return {"success": False, "error": f"Proyecto '{project_id}' no encontrado"}

    folder_path = project["folder_path"]
    project_name = project["name"]

    if resource_key == "docs":
        docs_dir = os.path.join(folder_path, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        readme_doc = os.path.join(docs_dir, "00_Indice_Documentacion.md")
        if not os.listdir(docs_dir):
            with open(readme_doc, "w", encoding="utf-8") as f:
                f.write(
                    f"# Documentación Técnica — {project_name}\n\n"
                    f"- **Carpeta del proyecto:** `{folder_path}`\n"
                    f"- **Categoría:** {project['category']}\n"
                    f"- **Descripción:** {project['description']}\n"
                )
        conn.close()
        subprocess.Popen(["explorer.exe", docs_dir])
        return {
            "success": True,
            "message": f"Abierta carpeta /docs de {project_name} en el Explorador",
            "target": docs_dir
        }

    elif resource_key == "onenote":
        onenote_url = project["onenote_url"] if "onenote_url" in project.keys() else None
        conn.close()
        if onenote_url:
            open_url_in_system_browser(onenote_url)
            return {
                "success": True,
                "message": f"Abriendo sección de {project_name} en OneNote (Desarrollo Proyectos)",
                "target": onenote_url
            }
        onenote_shortcut = r"D:\OneDrive\01_Gestion\Bloc de notas de Guillermo.url"
        if os.path.exists(onenote_shortcut):
            open_url_in_system_browser(onenote_shortcut)
            return {
                "success": True,
                "message": f"Abriendo Bloc de notas de Guillermo en OneNote ({project_name})",
                "target": onenote_shortcut
            }
        else:
            fallback_url = "https://www.onenote.com/notebooks"
            open_url_in_system_browser(fallback_url)
            return {
                "success": True,
                "message": "Abriendo OneNote Web",
                "target": fallback_url
            }

    elif resource_key == "git":
        conn.close()
        git_url = _extract_git_remote_url(folder_path)
        open_url_in_system_browser(git_url)
        return {
            "success": True,
            "message": f"Abriendo repositorio Git en el navegador ({git_url})",
            "target": git_url
        }

    elif resource_key == "skills":
        conn.close()
        skills_dir = os.path.join(WORKSPACE_ROOT, "0000_Utilidades", "01_Skills")
        skills_summary_file = os.path.join(skills_dir, "00_INDICE_SKILLS_Y_PATRONES.txt")

        # Asegurar que la carpeta existe
        os.makedirs(skills_dir, exist_ok=True)

        if os.path.exists(skills_dir):
            try:
                subprocess.Popen(["explorer.exe", skills_dir])
            except Exception as e:
                logger.error(f"Error al abrir explorer para skills: {e}")

        if os.path.exists(skills_summary_file):
            try:
                os.startfile(skills_summary_file)
            except Exception as e:
                logger.error(f"Error al abrir skills_summary_file con startfile: {e}")

        return {
            "success": True,
            "message": "Abierta carpeta de Skills y documento resumen de patrones y herramientas",
            "target": skills_summary_file
        }

    elif resource_key == "validation":
        cursor.execute("SELECT title, status, milestone_type, milestone_target, milestone_result FROM tasks WHERE project_id = ? ORDER BY order_index ASC", (project_id,))
        tasks = cursor.fetchall()
        conn.close()

        val_dir = os.path.join(folder_path, "validacion")
        os.makedirs(val_dir, exist_ok=True)
        report_file = os.path.join(val_dir, "ESTADO_VALIDACION.txt")

        port = project["port"]
        port_status = "No aplica (Sin puerto local)"
        if port:
            is_open = check_port_open("127.0.0.1", port)
            port_status = f"Puerto :{port} -> {'ACTIVO (200 OK / Escuchando)' if is_open else 'INACTIVO'}"

        has_docs = os.path.exists(os.path.join(folder_path, "docs"))
        has_git = os.path.exists(os.path.join(folder_path, ".git"))

        lines = [
            "====================================================================",
            f"  INFORME DE VALIDACIÓN TÉCNICA — {project_name.upper()}",
            f"  Fecha: { time.strftime('%d/%m/%Y %H:%M:%S') }",
            "====================================================================",
            "",
            f"📁 Carpeta del proyecto : {folder_path}",
            f"🌐 Estado del servidor  : {port_status}",
            f"📚 Carpeta /docs        : {'✅ Presente' if has_docs else '⚠️ Pendiente de crear'}",
            f"🐙 Repositorio Git      : {'✅ Inicializado (.git)' if has_git else '⚠️ Sin repositorio local'}",
            "",
            "--------------------------------------------------------------------",
            "  ESTADO DE HITOS Y VALIDACIONES DEL PROYECTO",
            "--------------------------------------------------------------------"
        ]
        for idx, t in enumerate(tasks, 1):
            st_label = "✅ COMPLETADO" if t["status"] == "completed" else ("⏳ EN PROGRESO" if t["status"] == "in_progress" else "⬜ PENDIENTE")
            lines.append(f"{idx}. [{st_label}] {t['title']} (Tipo: {t['milestone_type']})")
            if t["milestone_target"]:
                lines.append(f"   Objetivo : {t['milestone_target']}")
            if t["milestone_result"]:
                lines.append(f"   Resultado: {t['milestone_result']}")
            lines.append("")

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        subprocess.Popen(["explorer.exe", val_dir])
        os.startfile(report_file)

        return {
            "success": True,
            "message": f"Abierta carpeta /validacion e informe de estado de {project_name}",
            "target": report_file
        }

    conn.close()
    return {"success": False, "error": f"Recurso '{resource_key}' no reconocido"}
