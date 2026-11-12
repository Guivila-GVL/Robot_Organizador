import os
import json
import time
import threading
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.database import get_db_connection
from app.services.execution_queue import get_launched_queue, update_task_progress
from app.services.watchdog_service import (
    get_watchdog_status,
    mark_model_exhausted_hours,
    mark_model_exhausted_from_output,
    canonical_model_name,
    QUOTA_KEYWORDS
)
from app.services.milestone_checker import check_and_complete_task
from app.services.telegram_service import send_telegram_message
from app.services.activity_logger import log_activity

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
    "last_log": "En espera (pulsa ▶️ Avanzar Secuencia para iniciar)",
    "history": [],
    "auto_advance": True,
    "mode": "continuous"
}


def _log_event(msg: str) -> None:
    line = log_activity("RUNNER", msg)
    RUNNER_STATE["last_log"] = line
    RUNNER_STATE["history"].append(line)
    if len(RUNNER_STATE["history"]) > 60:
        RUNNER_STATE["history"] = RUNNER_STATE["history"][-60:]


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
        "history": list(RUNNER_STATE["history"][-30:]),
        "agy_available": os.path.exists(AGY_EXE),
        "auto_advance": RUNNER_STATE.get("auto_advance", True),
        "mode": RUNNER_STATE.get("mode", "continuous")
    }


def _pick_next_available_model(tried_models: List[str]) -> Optional[Dict[str, Any]]:
    canonical_tried = [canonical_model_name(t) for t in tried_models]
    wd = get_watchdog_status()
    models = wd.get("models", [])
    # 1. Preferir primero motores no agotados con cuota razonable (> 10%)
    for m in models:
        c_name = canonical_model_name(m["name"])
        if c_name in canonical_tried:
            continue
        if not m.get("is_exhausted") and m.get("quota_remaining_pct", 0) > 10:
            return m
    # 2. Respaldo: cualquier motor no agotado con algo de cuota
    for m in models:
        c_name = canonical_model_name(m["name"])
        if c_name in canonical_tried:
            continue
        if not m.get("is_exhausted") and m.get("quota_remaining_pct", 0) > 0:
            return m
    return None


def _build_headless_prompt(task: Dict[str, Any]) -> str:
    folder = task.get("folder_path") or WORKSPACE_ROOT
    val_text = task.get("validation") or task.get("milestone_description") or task.get("milestone_target") or "Funcionamiento técnico validado"
    target_info = f" (Objetivo técnico: `{task['milestone_target']}`)" if task.get("milestone_target") else ""
    return (
        f"Ejecuta de principio a fin la siguiente tarea del proyecto '{task['project_name']}' "
        f"ubicado en `{folder}`:\n\n"
        f"- ID Tarea: {task['id']}\n"
        f"- Título: {task['title']}\n"
        f"- Descripción / Prompt: {task.get('description') or task['title']}\n"
        f"- Validación (Cómo se va a validar): {val_text}{target_info}\n\n"
        f"Reglas de ejecución obligatorias:\n"
        f"1. Implementa los cambios necesarios en `{folder}` y valida el resultado ejecutando pruebas reales acordes a: `{val_text}`.\n"
        f"2. IMPORTANTE: NO detengas ni reinicies el servidor FastAPI del puerto 8002 (`pythonw.exe` / `uvicorn` de RobotOrganizador), "
        f"porque ese proceso aloja el ejecutor de la Cola Global que te está supervisando.\n"
        f"3. Durante la ejecución, reporta avances obligatorios por Telegram a `http://127.0.0.1:8002/api/tasks/{task['id']}/progress` (urllib PATCH):\n"
        f"   - Hito 1 (~20%): {{\"progress_pct\": 20, \"stage\": \"plan\", \"current_step\": \"Ya se ha pensado en cómo implementarlo: [diseño/estrategia]\"}}\n"
        f"   - Hito 2 (~50%): {{\"progress_pct\": 50, \"stage\": \"development\", \"current_step\": \"Comienza el desarrollo: [cambios en código]\"}}\n"
        f"   - Hito 3 (~80%): {{\"progress_pct\": 80, \"stage\": \"validation\", \"current_step\": \"Ha acabado el desarrollo y ahora comienza la validación: [pruebas]\"}}\n"
        f"4. Al terminar y verificar que todo funciona según la validación definida, CIERRA la tarea llamando por HTTP POST a "
        f"`http://127.0.0.1:8002/api/tasks/{task['id']}/check` con JSON `{{\"force_status\": \"completed\", \"comment\": \"Resumen técnico de lo realizado y verificado\"}}` "
        f"y devuelve un resumen conciso."
    )


def _run_single_task_with_model(task: Dict[str, Any], model_info: Dict[str, Any]) -> Dict[str, Any]:
    global _active_process

    task_id = task["id"]
    model_name = canonical_model_name(model_info["name"])
    cli_id = model_info["cli_id"]
    project_folder = task.get("folder_path") or WORKSPACE_ROOT
    if not os.path.exists(project_folder):
        project_folder = WORKSPACE_ROOT

    RUNNER_STATE["current_model"] = model_name
    _log_event(f"🚀 Ejecutando tarea #{task_id} con motor: {model_name} ({cli_id})")

    # Notificar por Telegram el arranque de la nueva tarea con hora exacta y motor
    start_time_str = datetime.now().strftime("%H:%M:%S (%d/%m/%Y)")
    try:
        from app.services.telegram_service import notify_task_started
        notify_task_started(
            project_name=task["project_name"],
            task_title=task["title"],
            task_id=task_id,
            model_name=model_name,
            started_at=start_time_str
        )
        conn = get_db_connection()
        conn.execute("""
            UPDATE tasks
            SET notified_stages = CASE
                WHEN notified_stages IS NULL OR notified_stages = '' THEN 'started'
                WHEN notified_stages NOT LIKE '%started%' THEN notified_stages || ',started'
                ELSE notified_stages
            END
            WHERE id = ?
        """, (task_id,))
        conn.commit()
        conn.close()
    except Exception as _e_tg:
        _log_event(f"Aviso Telegram al arrancar tarea #{task_id}: {_e_tg}")

    update_task_progress(
        task_id=task_id,
        progress_pct=max(10, task.get("progress_pct") or 10),
        current_step=f"⚡ Ejecutando con {model_name}...",
        note=f"Worker autónomo iniciado con motor {model_name}.",
        author="Cola Global",
        stage="started",
        notify_telegram=False
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
        sub_env = os.environ.copy()
        sub_env["PYTHONUNBUFFERED"] = "1"
        sub_env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.Popen(
            cmd,
            cwd=project_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
            env=sub_env
        )
        _active_process = proc
        output_lines: List[str] = []
        hb_stop = threading.Event()
        start_ts = time.time()

        def _heartbeat():
            while not hb_stop.wait(15.0):
                if proc.poll() is not None or RUNNER_STATE["stop_requested"]:
                    break
                elapsed_s = int(time.time() - start_ts)
                _log_event(f"⏳ [{model_name}] Procesando tarea #{task_id} en segundo plano ({elapsed_s}s)...")

        hb_thread = threading.Thread(target=_heartbeat, daemon=True)
        hb_thread.start()

        if proc.stdout:
            for line in proc.stdout:
                if RUNNER_STATE["stop_requested"]:
                    proc.terminate()
                    break
                clean_ln = line.strip()
                if clean_ln:
                    output_lines.append(clean_ln)
                    _log_event(f"[{model_name}] {clean_ln[:140]}")

        hb_stop.set()
        rc = proc.wait(timeout=30)
        _active_process = None
        full_output = "\n".join(output_lines)
        lower_out = full_output.lower()

        # Solo es error de cuota si el proceso falló (rc != 0) Y la salida contiene indicadores reales de error de cuota
        is_quota_err = (rc != 0) and any(k in lower_out for k in QUOTA_KEYWORDS)
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
        _log_event("🔄 Worker Autónomo de Cola Global iniciado (Modo Continuo activo).")
        while not RUNNER_STATE["stop_requested"]:
            queue_data = get_launched_queue()
            tasks = queue_data.get("tasks", [])
            if not tasks:
                _log_event("🏁 Todas las tareas de la Cola Global han finalizado con éxito.")
                try:
                    send_telegram_message("🏁 <b>Cola Global Completada:</b> Se han ejecutado con éxito todas las tareas de la secuencia.")
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
                    reset_dt = mark_model_exhausted_from_output(model_info["name"], res.get("output", ""))
                    from datetime import timezone
                    now_u = datetime.now(timezone.utc)
                    rem_secs = max(0, int((reset_dt - now_u).total_seconds()))
                    days = rem_secs // 86400
                    hrs = (rem_secs % 86400) // 3600
                    mins = (rem_secs % 3600) // 60
                    reset_desc = f"{days}d {hrs}h" if days > 0 else (f"{hrs}h {mins:02d}m" if hrs > 0 else f"{mins}m")
                    next_m = _pick_next_available_model(tried_models)
                    if next_m:
                        try:
                            send_telegram_message(
                                f"🔀 <b>Salto Automático de Motor:</b>\n"
                                f"• Agotado: <b>{model_info['name']}</b> (⏳ Renueva en {reset_desc})\n"
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
                    
                    # Verificación inmediata de siguientes tareas para avance continuo sin pausas
                    next_q = get_launched_queue()
                    remaining = next_q.get("tasks", [])
                    if remaining:
                        nxt = remaining[0]
                        _log_event(f"🔄 Avanzando inmediatamente a la siguiente tarea: #{nxt['id']} [{nxt['project_name']}] {nxt['title'][:55]}...")
                    task_finished = True
                    break
                else:
                    _log_event(f"⚠️ Motor {model_info['name']} devolvió código {res.get('returncode')}. Probando respaldo...")
                    # Si falló por error de modelo/red distinto de 429, intentar con el siguiente motor una vez
                    if len(tried_models) < 2:
                        continue

                    # Para evitar bloquear la cola completa, apartar esta tarea a pendientes y continuar con la siguiente
                    from app.services.execution_queue import pause_task
                    _log_event(f"⚠️ Tarea #{task_id} apartada para revisión tras fallar motor {model_info['name']}. Continuando con la siguiente tarea de la cola...")
                    update_task_progress(
                        task_id,
                        current_step=f"⚠️ Revisión manual requerida ({model_info['name']})",
                        note=f"Error en ejecución automática: {res.get('output', '')[:250]}",
                        author="Cola Global"
                    )
                    pause_task(task_id)
                    try:
                        send_telegram_message(
                            f"⚠️ <b>Tarea #{task_id} Pausada por Incidencia:</b>\n"
                            f"• Proyecto: {task['project_name']}\n"
                            f"• Tarea: {task['title']}\n"
                            f"• Detalle: Fallo en motor {model_info['name']}.\n"
                            f"🔄 <b>Continuando automáticamente</b> con la siguiente tarea de la cola..."
                        )
                    except Exception:
                        pass
                    task_finished = True
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
        _log_event("⏸️ Cola Global puesta en pausa por el usuario.")
        try:
            send_telegram_message("⏸️ <b>Cola Global Pausada:</b> Ejecución detenida manualmente. Las tareas restantes quedan en cola a la espera de que pulses ▶️ Avanzar.")
        except Exception:
            pass

        if _active_process and _active_process.poll() is None:
            try:
                _active_process.terminate()
            except Exception:
                pass
        return {"success": True, "stopping": True, "status": get_runner_status()}

