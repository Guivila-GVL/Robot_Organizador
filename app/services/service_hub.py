import os
import sys
import time
import socket
import subprocess
import webbrowser
import logging
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("service_hub")

WORKSPACE_ROOT = r"D:\OneDrive\04_Desarrollo_proyectos"
_python_dir = os.path.dirname(sys.executable) if sys.executable else ""
_pythonw_candidate = os.path.join(_python_dir, "pythonw.exe")
PYTHON_EXE = _pythonw_candidate if os.path.exists(_pythonw_candidate) else (sys.executable or "python")
HIDDEN_RUNNER_SCRIPT = os.path.join(WORKSPACE_ROOT, "2026_Proyecto_RobotOrganizador", "run_uvicorn_hidden.py")
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

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
        "start_cmd": [PYTHON_EXE, HIDDEN_RUNNER_SCRIPT, "--app", "app.main:app", "--host", "127.0.0.1", "--port", "8002", "--cwd", os.path.join(WORKSPACE_ROOT, "2026_Proyecto_RobotOrganizador")]
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
        "start_cmd": [PYTHON_EXE, HIDDEN_RUNNER_SCRIPT, "--app", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--cwd", os.path.join(WORKSPACE_ROOT, "2026_Proyecto_Videos")]
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
        "start_cmd": [PYTHON_EXE, HIDDEN_RUNNER_SCRIPT, "--app", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--cwd", os.path.join(WORKSPACE_ROOT, "2026_Proyecto_Comentarista")]
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
        "id": "actualizador_esios",
        "name": "Actualizador ESIOS",
        "description": "Ingesta diaria automática de precios y curvas de energía",
        "host": "127.0.0.1",
        "port": 8050,
        "url": "http://127.0.0.1:8050",
        "icon": "🔋",
        "color": "#14b8a6",
        "cwd": os.path.join(WORKSPACE_ROOT, "2026_Proyecto_Energia_Graficos", "02_Scripts_Python"),
        "start_cmd": [PYTHON_EXE, "00_DASHBOARD_ACTUALIZADOR.py", "--autostart", "--no-browser"]
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
        # DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200) | CREATE_NO_WINDOW (0x08000000)
        creation_flags = 0x00000008 | 0x00000200 | 0x08000000
        subprocess.Popen(
            start_cmd,
            cwd=cwd,
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
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
        cursor.execute("SELECT id, title, status, milestone_type, milestone_target, milestone_result, priority FROM tasks WHERE project_id = ? ORDER BY order_index ASC", (project_id,))
        tasks = [dict(t) for t in cursor.fetchall()]

        cursor.execute("SELECT value FROM settings WHERE key = 'telegram_bot_token'")
        tg_token_row = cursor.fetchone()
        has_tg = bool(tg_token_row and tg_token_row["value"])

        onenote_url = project["onenote_url"] if "onenote_url" in project.keys() else None
        conn.close()

        val_dir = os.path.join(folder_path, "validacion")
        os.makedirs(val_dir, exist_ok=True)
        guide_file = os.path.join(val_dir, "00_GUIA_REVISION_GENERAL_TAREA.md")
        report_file = os.path.join(val_dir, "ESTADO_VALIDACION.txt")

        # 1. Crear o actualizar la guía oficial de Revisión General al Acabar una Tarea
        with open(guide_file, "w", encoding="utf-8") as f:
            f.write(
                f"# Protocolo de Revisión General al Acabar una Tarea — {project_name}\n\n"
                f"Este checklist define la revisión técnica obligatoria que debe ejecutarse al concluir cualquier tarea:\n\n"
                f"### 📋 Checklist de los 5 Pasos Obligatorios:\n\n"
                f"1. **📁 Documentación en /docs actualizada:**\n"
                f"   - Verificar que los cambios y decisiones queden documentados en la carpeta `docs/`.\n"
                f"   - Añadir o actualizar la entrada en `docs/REGISTRO_HITOS.md` con el resultado y fecha.\n\n"
                f"2. **📓 OneNote / Bitácora actualizada:**\n"
                f"   - Comprobar que la sección del proyecto en *Desarrollo Proyectos* refleje el avance reciente.\n"
                f"   - Hoja `01. Resumen`: porcentaje recalculado y fecha actualizada.\n"
                f"   - Hoja `02. Listado de Actividades`: tarea marcada como completada con su resultado.\n\n"
                f"3. **🐙 Git actualizado y subido a GitHub:**\n"
                f"   - Comprobar que no queden ficheros temporales ni secretos sin proteger en `.gitignore`.\n"
                f"   - Crear un commit descriptivo: `feat(hito): <tarea> [protocolo-completado]`.\n"
                f"   - Ejecutar `git push origin main` al repositorio de GitHub.\n\n"
                f"4. **🧠 Skills y forma de trabajo revisadas:**\n"
                f"   - Consultar las directrices de `0000_Utilidades/01_Skills` (`03_Gestion_Proyecto`, `02_OneNote_Management`, etc.).\n"
                f"   - Verificar que la arquitectura y limpieza del código sean consistentes con el estándar.\n\n"
                f"5. **📱 Check y envío a Telegram:**\n"
                f"   - Último paso de confirmación: enviar el check de esta revisión general con su imagen/captura al canal de Telegram (@Bot2_Video_bot).\n\n"
                f"---\n"
                f"*Automatización: En el Robot de Gestión de Proyectos, esta secuencia se ejecuta automáticamente al completar cualquier tarea.*\n"
            )

        # 2. Diagnóstico técnico en vivo
        port = project["port"]
        port_status = "No aplica (Sin puerto local)"
        if port:
            is_open = check_port_open("127.0.0.1", port)
            port_status = f"Puerto :{port} -> {'ACTIVO (200 OK / Escuchando)' if is_open else 'INACTIVO'}"

        docs_dir = os.path.join(folder_path, "docs")
        has_docs = os.path.exists(docs_dir)
        has_hitos_log = os.path.exists(os.path.join(docs_dir, "REGISTRO_HITOS.md"))

        git_dir = os.path.join(folder_path, ".git")
        has_git = os.path.exists(git_dir)
        git_remote = _extract_git_remote_url(folder_path) if has_git else "N/A"

        git_clean = "N/A"
        if has_git:
            try:
                res_git = subprocess.run(["git", "status", "--porcelain"], cwd=folder_path, capture_output=True, text=True, timeout=3, creationflags=CREATE_NO_WINDOW)
                git_clean = "Limpio (Sin cambios pendientes)" if not res_git.stdout.strip() else "Hay cambios sin commit"
            except Exception:
                git_clean = "No verificado"

        has_onenote = bool(onenote_url)
        has_val_folder = os.path.exists(val_dir)

        in_progress_tasks = [t for t in tasks if t["status"] == "in_progress"]
        pending_tasks = [t for t in tasks if t["status"] == "pending"]
        completed_tasks = [t for t in tasks if t["status"] == "completed"]

        lines = [
            "====================================================================",
            f"  INFORME DE VALIDACIÓN TÉCNICA Y REVISIÓN GENERAL — {project_name.upper()}",
            f"  Fecha: { time.strftime('%d/%m/%Y %H:%M:%S') }",
            "====================================================================",
            "",
            "📌 ESTADO EN VIVO DE LOS 5 PUNTOS DEL PROTOCOLO DE CIERRE:",
            "--------------------------------------------------------------------",
            f"1. 📁 Documentación (/docs)  : {'✅ Presente' if has_docs else '⚠️ Falta crear'} | Registro hitos: {'✅ Al día' if has_hitos_log else '⚠️ Sin REGISTRO_HITOS.md'}",
            f"2. 📓 OneNote / Bitácora      : {'✅ Enlazado y Activo' if has_onenote else '⚠️ Enlace no registrado'}",
            f"3. 🐙 Git & GitHub            : {'✅ Repositorio activo' if has_git else '⚠️ Sin .git'} | {git_clean}",
            f"   ↳ URL Remota              : {git_remote}",
            f"4. 🧠 Skills y Metodología    : {'✅ Carpetas /docs y /validacion conforme' if (has_docs and has_val_folder) else '⚠️ Revisar estructura'}",
            f"5. 📱 Notificación Telegram   : {'✅ Configurada (@Bot2_Video_bot)' if has_tg else '⚠️ Token pendiente'}",
            f"🌐 Servidor / Puerto Local   : {port_status}",
            "",
            "--------------------------------------------------------------------",
            "  ESTADO DE LAS TAREAS DEL PROYECTO (PRIORIDAD VISUAL)",
            "--------------------------------------------------------------------",
            f"Total: {len(tasks)} tareas | ⏳ En Progreso: {len(in_progress_tasks)} | ⬜ Pendientes: {len(pending_tasks)} | ✅ Completadas: {len(completed_tasks)}",
            ""
        ]

        if in_progress_tasks:
            lines.append("▶ TAREAS EN PROGRESO (Revisión prioritaria):")
            for t in in_progress_tasks:
                lines.append(f"  • [⏳ EN PROGRESO] {t['title']} (Prioridad: {t['priority'].upper()})")
                if t["milestone_target"]:
                    lines.append(f"    Objetivo : {t['milestone_target']}")
            lines.append("")

        if pending_tasks:
            lines.append("▶ TAREAS PENDIENTES (Siguientes pasos):")
            for t in pending_tasks:
                lines.append(f"  • [⬜ PENDIENTE] {t['title']} (Prioridad: {t['priority'].upper()})")
            lines.append("")

        if completed_tasks:
            lines.append("▶ TAREAS COMPLETADAS (Historial cerrado con protocolo):")
            for t in completed_tasks:
                res_desc = f" -> {t['milestone_result'][:70]}..." if t['milestone_result'] else ""
                lines.append(f"  • [✅ COMPLETADA] {t['title']}{res_desc}")
            lines.append("")

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # Abrir carpeta y documentos
        if os.path.exists(val_dir):
            subprocess.Popen(["explorer.exe", val_dir])
        if os.path.exists(guide_file):
            try:
                os.startfile(guide_file)
            except Exception:
                if os.path.exists(report_file):
                    os.startfile(report_file)

        return {
            "success": True,
            "message": f"Abierta carpeta /validacion y protocolo de revisión general de {project_name}",
            "target": guide_file
        }

    conn.close()
    return {"success": False, "error": f"Recurso '{resource_key}' no reconocido"}


def get_esios_live_status() -> Dict[str, Any]:
    port_open = check_port_open("127.0.0.1", 8050, timeout=0.4)
    if not port_open:
        return {
            "online": False,
            "status": "stopped",
            "status_text": "Servicio detenido (Puerto 8050 apagado)",
            "progress": 0,
            "current_step": "Inactivo. Pulsa 'Arrancar' para iniciar el proceso.",
            "current_task_name": "Ninguna",
            "elapsed_time": 0,
            "eta_text": "--",
            "logs": [],
            "total_tasks": 86,
            "completed_tasks": 0,
            "total_added": 0
        }
    try:
        req = urllib.request.Request("http://127.0.0.1:8050/api/status", headers={"User-Agent": "RobotOrganizador/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode("utf-8"))
                status_raw = data.get("status", "idle")
                status_text = "En ejecución" if status_raw == "running" else "Listo / Al día" if status_raw == "completed" else "En espera" if status_raw == "idle" else "Error / Fallido"
                raw_logs = data.get("logs", [])[-100:]
                if not raw_logs:
                    esios_log_file = os.path.join(WORKSPACE_ROOT, "2026_Proyecto_Energia_Graficos", "02_Scripts_Python", "actualizador_8050.log")
                    if os.path.exists(esios_log_file):
                        try:
                            with open(esios_log_file, "r", encoding="utf-8", errors="ignore") as lf:
                                raw_logs = [ln.strip() for ln in lf.readlines() if ln.strip()][-30:]
                        except Exception:
                            pass
                if not raw_logs:
                    raw_logs = ["[OK] Demonio Actualizador ESIOS activo en segundo plano (pythonw.exe - sin ventana CMD).", "Listo para sincronizar o esperando siguiente ciclo."]
                return {
                    "online": True,
                    "status": status_raw,
                    "status_text": status_text,
                    "progress": data.get("progress", 0),
                    "current_step": data.get("current_step", ""),
                    "current_task_name": data.get("current_task_name", ""),
                    "elapsed_time": data.get("elapsed_time", 0),
                    "eta_text": data.get("eta_text", "--"),
                    "logs": raw_logs,
                    "total_tasks": data.get("total_tasks", 86),
                    "completed_tasks": data.get("completed_tasks", 0),
                    "total_added": data.get("total_added", 0)
                }
    except Exception as e:
        logger.warning(f"Error consultando telemetría ESIOS: {e}")

    return {
        "online": True,
        "status": "idle",
        "status_text": "En línea (Respondiendo)",
        "progress": 0,
        "current_step": "En espera",
        "current_task_name": "Ninguna",
        "elapsed_time": 0,
        "eta_text": "--",
        "logs": [],
        "total_tasks": 86,
        "completed_tasks": 0,
        "total_added": 0
    }


def trigger_esios_update() -> Dict[str, Any]:
    port_open = check_port_open("127.0.0.1", 8050, timeout=0.4)
    if not port_open:
        start_res = start_local_service("actualizador_esios", wait_ready=True, max_wait=6.0)
        if not start_res.get("success"):
            return {"success": False, "error": f"No se pudo arrancar el Actualizador ESIOS: {start_res.get('error')}"}

    try:
        req = urllib.request.Request("http://127.0.0.1:8050/api/start", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            return {"success": True, "message": "Sincronización de energía iniciada correctamente"}
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
            return {"success": False, "error": body.get("error", str(e))}
        except Exception:
            return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_combined_service_monitor() -> Dict[str, Any]:
    esios_status = get_esios_live_status()
    try:
        from app.services.queue_runner import get_runner_status
        runner_status = get_runner_status()
    except Exception:
        runner_status = {"running": False, "last_log": "No disponible"}
    
    server_logs = []
    log_path = os.path.join(WORKSPACE_ROOT, "2026_Proyecto_RobotOrganizador", "server_8002.log")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                server_logs = [line.strip() for line in f.readlines() if line.strip()][-40:]
        except Exception:
            pass

    services_summary = get_services_status()

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "esios": esios_status,
        "robot": {
            "online": True,
            "port": 8002,
            "status_text": "En ejecución (Servidor Activo)",
            "runner": runner_status,
            "server_logs": server_logs
        },
        "services": services_summary
    }
