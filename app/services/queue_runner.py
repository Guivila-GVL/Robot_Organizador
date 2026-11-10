import os
import json
import time
import threading
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.database import get_db_connection
from app.services.execution_queue import get_launched_queue, update_task_progress
from app.services.watchdog_service import get_watchdog_status, mark_model_exhausted_hours, QUOTA_KEYWORDS
from app.services.milestone_checker import check_and_complete_task
from app.services.telegram_service import send_telegram_message

AGY_EXE = r"C:\Users\guill\.gemini\bin\agy.exe"
WORKSPACE_ROOT = r"D:\OneDrive\04_Desarrollo_proyectos"

_runner_lock = threading.Lock()
_active_process: Optional[subprocess.Popen] = None

RUNNER_STATE: Dict[str, Any] = {
    "running": False,
    "stop_requested": False,
    "current_task_id": None,
    "current_task_title": "",
    "current_project_name": "",
    "current_model": "",
    "started_at": None,
    "last_log": "En espera (pulsa ▶️ Ejecutar Secuencia Ahora para iniciar)",
    "history": []
}


def _log_event(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    RUNNER_STATE["last_log"] = line
    RUNNER_STATE["history"].append(line)
    if len(RUNNER_STATE["history"]) > 30:
        RUNNER_STATE["history"] = RUNNER_STATE["history"][-30:]
    try:
        print(f"[RUNNER] {line}", flush=True)
    except Exception:
        pass


def get_runner_status() -> Dict[str, Any]:
    return {
        "running": RUNNER_STATE["running"],
        "stop_requested": RUNNER_STATE["stop_requested"],
        "current_task_id": RUNNER_STATE["current_task_id"],
        "current_task_title": RUNNER_STATE["current_task_title"],
        "current_project_name": RUNNER_STATE["current_project_name"],
        "current_model": RUNNER_STATE["current_model"],
        "started_at": RUNNER_STATE["started_at"],
        "last_log": RUNNER_STATE["last_log"],
        "history": list(RUNNER_STATE["history"][-10:]),
        "agy_available": os.path.exists(AGY_EXE)
    }


def _pick_next_available_model(tried_models: List[str]) -> Optional[Dict[str, Any]]:
    wd = get_watchdog_status()
    models = wd.get("models", [])
    for m in models:
        if m["name"] in tried_models:
            continue
        if not m.get("is_exhausted") and m.get("quota_remaining_pct", 0) > 0:
            return m
    return None


def _build_headless_prompt(task: Dict[str, Any]) -> str:
    folder = task.get("folder_path") or WORKSPACE_ROOT
    milestone_info = task.get("milestone_description") or task.get("milestone_target") or "Funcionamiento técnico validado"
    return (
        f"Ejecuta de principio a fin la siguiente tarea del proyecto '{task['project_name']}' "
        f"ubicado en `{folder}`:\n\n"
        f"- ID Tarea: {task['id']}\n"
        f"- Título: {task['title']}\n"
        f"- Descripción: {task.get('description') or task['title']}\n"
        f"- Criterio de éxito: {milestone_info}\n\n"
        f"Reglas de ejecución:\n"
        f"1. Implementa los cambios necesarios en `{folder}` y pruébalos con comandos reales.\n"
        f"2. Durante la ejecución, reporta avances a `http://127.0.0.1:8002/api/tasks/{task['id']}/progress` "
        f"(ej. con Python urllib PATCH `{{\"progress_pct\": 60, \"current_step\": \"...\"}}`).\n"
        f"3. Cuando hayas comprobado que todo funciona, devuelve un resumen técnico conciso de lo realizado y verificado."
    )


def _run_single_task_with_model(task: Dict[str, Any], model_info: Dict[str, Any]) -> Dict[str, Any]:
    global _active_process

    task_id = task["id"]
    model_name = model_info["name"]
    cli_id = model_info["cli_id"]
    project_folder = task.get("folder_path") or WORKSPACE_ROOT
    if not os.path.exists(project_folder):
        project_folder = WORKSPACE_ROOT

    RUNNER_STATE["current_model"] = model_name
    _log_event(f"🚀 Ejecutando tarea #{task_id} con motor: {model_name} ({cli_id})")

    update_task_progress(
        task_id=task_id,
        progress_pct=max(25, task.get("progress_pct") or 10),
        current_step=f"⚡ Ejecutando con {model_name}...",
        note=f"Worker autónomo iniciado con motor {model_name}.",
        author="Cola Global"
    )

    prompt = _build_headless_prompt(task)
    cmd = [
        AGY_EXE,
        "--mode", "auto",
        "--dangerously-skip-permissions",
        "--add-dir", WORKSPACE_ROOT,
        "--model", cli_id,
        f"--print={prompt}"
    ]

    try:
        creation_flags = 0x08000000  # CREATE_NO_WINDOW
        proc = subprocess.Popen(
            cmd,
            cwd=project_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags
        )
        _active_process = proc
        output_lines: List[str] = []

        if proc.stdout:
            for line in proc.stdout:
                if RUNNER_STATE["stop_requested"]:
                    proc.terminate()
                    break
                clean_ln = line.strip()
                if clean_ln:
                    output_lines.append(clean_ln)
                    _log_event(f"[{model_name}] {clean_ln[:120]}")

        rc = proc.wait(timeout=30)
        _active_process = None
        full_output = "\n".join(output_lines)
        lower_out = full_output.lower()

        is_quota_err = any(k in lower_out for k in QUOTA_KEYWORDS)
        return {
            "returncode": rc,
            "quota_error": is_quota_err,
            "output": full_output[-1200:] if full_output else ""
        }
    except Exception as e:
        _active_process = None
        return {
            "returncode": -1,
            "quota_error": False,
            "output": str(e)
        }


def _runner_loop() -> None:
    try:
        _log_event("🔄 Worker Autónomo de Cola Global iniciado.")
        while not RUNNER_STATE["stop_requested"]:
            queue_data = get_launched_queue()
            tasks = queue_data.get("tasks", [])
            if not tasks:
                _log_event("✅ Todas las tareas de la Cola Global han finalizado.")
                try:
                    send_telegram_message("🎉 <b>Cola Global Completada:</b> No quedan tareas pendientes en ejecución.")
                except Exception:
                    pass
                break

            task = tasks[0]
            task_id = task["id"]
            RUNNER_STATE["current_task_id"] = task_id
            RUNNER_STATE["current_task_title"] = task["title"]
            RUNNER_STATE["current_project_name"] = task["project_name"]

            tried_models: List[str] = []
            task_finished = False

            while not RUNNER_STATE["stop_requested"]:
                model_info = _pick_next_available_model(tried_models)
                if not model_info:
                    _log_event("⏳ Todos los motores disponibles están agotados (429). Deteniendo cola.")
                    update_task_progress(
                        task_id,
                        current_step="⏳ Pausada: todos los motores agotados temporalmente",
                        note="Todos los motores configurados alcanzaron límite 429.",
                        author="Cola Global"
                    )
                    try:
                        send_telegram_message("⚠️ <b>Cola Global Pausada:</b> Todos los motores configurados están temporalmente sin cuota (429).")
                    except Exception:
                        pass
                    RUNNER_STATE["stop_requested"] = True
                    break

                tried_models.append(model_info["name"])
                res = _run_single_task_with_model(task, model_info)

                if RUNNER_STATE["stop_requested"]:
                    _log_event("⏹️ Ejecución detenida manualmente por el usuario.")
                    break

                if res.get("quota_error"):
                    _log_event(f"⚠️ {model_info['name']} alcanzó límite de cuota (429). Saltando al siguiente motor...")
                    mark_model_exhausted_hours(model_info["name"], 5)
                    next_m = _pick_next_available_model(tried_models)
                    if next_m:
                        try:
                            send_telegram_message(
                                f"🔀 <b>Salto Automático de Motor:</b>\n"
                                f"• Agotado: {model_info['name']}\n"
                                f"• Continuando con: <b>{next_m['name']}</b> ({next_m['quota_remaining_pct']}%)"
                            )
                        except Exception:
                            pass
                    continue

                if res.get("returncode") == 0:
                    # Comprobar si la tarea sigue abierta; si sí, cerrarla con el protocolo oficial
                    conn = get_db_connection()
                    row = conn.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
                    conn.close()

                    if row and row["status"] != "completed":
                        summary = res.get("output") or f"Tarea completada automáticamente por {model_info['name']}."
                        _log_event(f"📋 Ejecutando protocolo de cierre para tarea #{task_id}...")
                        update_task_progress(task_id, 95, "📋 Ejecutando protocolo de cierre (Docs, OneNote, Git, Telegram)...")
                        check_and_complete_task(
                            task_id=task_id,
                            comment=f"Completada automáticamente vía Cola Global ({model_info['name']}):\n{summary[-500:]}",
                            force_status="completed"
                        )
                    _log_event(f"✅ Tarea #{task_id} completada con éxito.")
                    task_finished = True
                    break
                else:
                    _log_event(f"⚠️ Motor {model_info['name']} devolvió código {res.get('returncode')}. Probando respaldo o cerrando ciclo.")
                    # Si falló por error de modelo/red distinto de 429, intentar con el siguiente motor una vez
                    if len(tried_models) < 2:
                        continue
                    update_task_progress(
                        task_id,
                        current_step=f"⚠️ Revisión manual requerida ({model_info['name']})",
                        note=f"Error en ejecución automática: {res.get('output', '')[:250]}",
                        author="Cola Global"
                    )
                    break

            if not task_finished and RUNNER_STATE["stop_requested"]:
                break
            time.sleep(1)

    finally:
        RUNNER_STATE["running"] = False
        RUNNER_STATE["stop_requested"] = False
        RUNNER_STATE["current_task_id"] = None
        RUNNER_STATE["current_task_title"] = ""
        RUNNER_STATE["current_project_name"] = ""
        RUNNER_STATE["current_model"] = ""


def start_queue_runner() -> Dict[str, Any]:
    with _runner_lock:
        if not os.path.exists(AGY_EXE):
            return {"success": False, "error": f"No se encontró el CLI de Antigravity en {AGY_EXE}"}

        if RUNNER_STATE["running"]:
            return {"success": True, "already_running": True, "status": get_runner_status()}

        q = get_launched_queue()
        if not q.get("tasks"):
            return {"success": False, "error": "No hay tareas 'En Progreso' en la Cola Global para ejecutar."}

        RUNNER_STATE["running"] = True
        RUNNER_STATE["stop_requested"] = False
        RUNNER_STATE["started_at"] = datetime.now().isoformat()
        RUNNER_STATE["history"] = []
        _log_event(f"▶️ Lanzando ejecución automática de {len(q['tasks'])} tarea(s) en secuencia...")

        t = threading.Thread(target=_runner_loop, daemon=True)
        t.start()

        return {"success": True, "started": True, "status": get_runner_status()}


def stop_queue_runner() -> Dict[str, Any]:
    global _active_process
    with _runner_lock:
        if not RUNNER_STATE["running"]:
            return {"success": True, "was_running": False, "status": get_runner_status()}

        RUNNER_STATE["stop_requested"] = True
        _log_event("⏹️ Solicitada detención del worker autónomo...")
        if _active_process and _active_process.poll() is None:
            try:
                _active_process.terminate()
            except Exception:
                pass
        return {"success": True, "stopping": True, "status": get_runner_status()}

