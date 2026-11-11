import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.database import get_db_connection
from app.services.activity_logger import log_activity

WORKSPACE_ROOT = r"D:\OneDrive\04_Desarrollo_proyectos"
QUEUE_FILE = os.path.join(WORKSPACE_ROOT, "0000_Utilidades", "COLA_EJECUCION_ANTIGRAVITY.md")

QUEUE_ORDER_SQL = """
    ORDER BY
        CASE WHEN COALESCE(t.queue_order, 0) > 0 THEN 0 ELSE 1 END ASC,
        COALESCE(t.queue_order, 0) ASC,
        t.launched_at ASC,
        t.id ASC
"""


def _normalize_queue_orders(cursor) -> List[Dict[str, Any]]:
    cursor.execute(f"""
        SELECT t.id, COALESCE(t.queue_order, 0) as queue_order
        FROM tasks t
        WHERE t.status = 'in_progress'
        {QUEUE_ORDER_SQL}
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    for idx, r in enumerate(rows, 1):
        if r["queue_order"] != idx:
            cursor.execute("UPDATE tasks SET queue_order = ? WHERE id = ?", (idx, r["id"]))
            r["queue_order"] = idx
    return rows


def sync_execution_queue_file() -> str:
    """Sincroniza todas las tareas en estado 'in_progress' en orden secuencial."""
    conn = get_db_connection()
    cursor = conn.cursor()
    _normalize_queue_orders(cursor)
    conn.commit()

    cursor.execute(f"""
        SELECT t.*, p.name as project_name, p.folder_name, p.folder_path
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.status = 'in_progress'
        {QUEUE_ORDER_SQL}
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    lines = [
        "# 🚀 Cola Global de Tareas Lanzadas (Secuencia de Ejecución)",
        "",
        f"*Actualizado automáticamente desde Robot de Gestión de Proyectos: {now_str}*",
        f"*Total tareas activas en ejecución: **{len(rows)}***",
        "",
        "---",
        ""
    ]

    if not rows:
        lines.append("No hay tareas en progreso en este momento.")
    else:
        for idx, t in enumerate(rows, 1):
            pct = t.get("progress_pct") or 0
            step = t.get("current_step") or "En cola de lanzamiento"
            lines.extend([
                f"## #{idx}. [{t['project_name']}] {t['title']} (ID `{t['id']}`)",
                f"- **Proyecto / Carpeta:** `{t['folder_path']}`",
                f"- **Prioridad:** {t['priority'].upper()} | **Progreso:** `{pct}%` — *{step}*",
                f"- **Descripción:** {t['description'] or 'Sin descripción adicional'}",
                f"- **Criterio de éxito ({t['milestone_type']}):** {t['milestone_description'] or t['milestone_target'] or 'Validación técnica estándar'}",
                ""
            ])

    lines.extend([
        "---",
        "### 📡 Instrucciones para el Agente (Tracking de Hitos Telegram + Cierre):",
        "1. Ejecuta las tareas estrictamente en el orden `#1 -> #2 -> #3...` definido arriba.",
        "2. Reporta los hitos intermedios obligatorios por Telegram vía `PATCH http://127.0.0.1:8002/api/tasks/{id}/progress`:",
        "   - Hito 1 (~20-25%): `{\"progress_pct\": 20, \"stage\": \"plan\", \"current_step\": \"Ya se ha pensado en cómo implementarlo: [estrategia]\"}`",
        "   - Hito 2 (~50%): `{\"progress_pct\": 50, \"stage\": \"development\", \"current_step\": \"Comienza el desarrollo: [implementación]\"}`",
        "   - Hito 3 (~80%): `{\"progress_pct\": 80, \"stage\": \"validation\", \"current_step\": \"Ha acabado el desarrollo y ahora comienza la validación: [pruebas]\"}`",
        "3. Al terminar y validar la tarea, ciérrala llamando a:",
        "   `POST http://127.0.0.1:8002/api/tasks/{id}/check` con `{\"force_status\": \"completed\", \"comment\": \"...\"}`",
        "   (Esto disparará automáticamente el protocolo en /docs, OneNote, GitHub, Skills y Telegram)."
    ])

    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return QUEUE_FILE


def launch_task(task_id: int) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()

    if not task:
        conn.close()
        return {"success": False, "error": f"Tarea {task_id} no encontrada"}

    now = datetime.now().isoformat()
    current_pct = task["progress_pct"] if "progress_pct" in task.keys() and task["progress_pct"] else 0
    new_pct = max(10, current_pct)
    step_text = "🚀 En cola de lanzamiento (lista para ejecutar)"

    cursor.execute("SELECT COALESCE(MAX(queue_order), 0) + 1 as next_q FROM tasks WHERE status = 'in_progress'")
    next_q = cursor.fetchone()["next_q"]
    existing_q = task["queue_order"] if "queue_order" in task.keys() and task["queue_order"] else 0
    final_q = existing_q if (task["status"] == "in_progress" and existing_q > 0) else next_q

    cursor.execute("""
        UPDATE tasks
        SET status = 'in_progress',
            progress_pct = ?,
            current_step = ?,
            queue_order = ?,
            launched_at = COALESCE(launched_at, ?)
        WHERE id = ?
    """, (new_pct, step_text, final_q, now, task_id))

    cursor.execute("""
        INSERT INTO comments (task_id, author, text, created_at)
        VALUES (?, 'Sistema', ?, ?)
    """, (task_id, "🚀 Tarea lanzada a 'En Progreso' y añadida a la Cola Global.", now))

    conn.commit()
    conn.close()

    log_activity("TAREA", f"🚀 #{task_id} lanzada a En Progreso: {task['title'][:70]}")
    queue_path = sync_execution_queue_file()
    return {
        "success": True,
        "task_id": task_id,
        "status": "in_progress",
        "progress_pct": new_pct,
        "queue_order": final_q,
        "current_step": step_text,
        "queue_file": queue_path
    }


def pause_task(task_id: int) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if not cursor.fetchone():
        conn.close()
        return {"success": False, "error": f"Tarea {task_id} no encontrada"}

    now = datetime.now().isoformat()
    step_text = "⏸️ Pausada en pendientes"

    cursor.execute("""
        UPDATE tasks
        SET status = 'pending',
            queue_order = 0,
            current_step = ?
        WHERE id = ?
    """, (step_text, task_id))

    cursor.execute("""
        INSERT INTO comments (task_id, author, text, created_at)
        VALUES (?, 'Sistema', ?, ?)
    """, (task_id, "⏸️ Tarea pausada y devuelta a la lista de Pendientes.", now))

    conn.commit()
    conn.close()

    log_activity("TAREA", f"⏸️ #{task_id} pausada y devuelta a Pendientes.")
    sync_execution_queue_file()
    return {"success": True, "task_id": task_id, "status": "pending"}


def reorder_queue_task(task_id: int, direction: str) -> Dict[str, Any]:
    """Sube ('up') o baja ('down') una tarea en la secuencia global de ejecución."""
    if direction not in ("up", "down"):
        return {"success": False, "error": "Dirección inválida. Usa 'up' o 'down'."}

    conn = get_db_connection()
    cursor = conn.cursor()
    rows = _normalize_queue_orders(cursor)

    idx = next((i for i, r in enumerate(rows) if r["id"] == task_id), None)
    if idx is None:
        conn.close()
        return {"success": False, "error": "La tarea no está en progreso en la cola activa"}

    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(rows):
        rows[idx], rows[swap_idx] = rows[swap_idx], rows[idx]
        for pos, r in enumerate(rows, 1):
            cursor.execute("UPDATE tasks SET queue_order = ? WHERE id = ?", (pos, r["id"]))
        conn.commit()

    conn.close()
    log_activity("COLA", f"🔀 Secuencia reordenada: tarea #{task_id} movida ({direction}).")
    sync_execution_queue_file()
    return {"success": True, "task_id": task_id, "direction": direction}


def normalize_stage(stage_or_step: Optional[str], pct: Optional[int] = None) -> Optional[str]:
    txt = (stage_or_step or "").lower().strip()
    if txt in ("started", "inicio", "comienzo", "start"):
        return "started"
    if txt in ("plan", "pensado", "pensar", "diseno", "diseño", "analisis", "análisis"):
        return "plan"
    if txt in ("development", "desarrollo", "dev", "implementacion", "implementación", "codificacion", "codificación"):
        return "development"
    if txt in ("validation", "validacion", "validación", "test", "pruebas", "verificacion", "verificación"):
        return "validation"

    # Detección por palabras clave en la descripción del paso
    if "comienza la validaci" in txt or "comenzando validaci" in txt or "acabado el desarrollo" in txt or "fin del desarrollo" in txt or "validación técnica" in txt:
        return "validation"
    if "comienza el desarrollo" in txt or "iniciando desarrollo" in txt or "fase de desarrollo" in txt or "implementando" in txt:
        return "development"
    if "pensado en c" in txt or "pensado como" in txt or "estrategia definida" in txt or "planificaci" in txt or "diseño t" in txt:
        return "plan"

    # Mapeo según el porcentaje de progreso estándar (20-25% plan, 50% dev, 80% val)
    if pct is not None:
        if 15 <= pct <= 35:
            return "plan"
        elif 45 <= pct <= 65:
            return "development"
        elif 75 <= pct <= 90:
            return "validation"

    return None


def update_task_progress(
    task_id: int,
    progress_pct: Optional[int] = None,
    current_step: Optional[str] = None,
    note: Optional[str] = None,
    author: str = "Agente",
    stage: Optional[str] = None,
    notify_telegram: Optional[bool] = None
) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, p.name as project_name
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.id = ?
    """, (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return {"success": False, "error": f"Tarea {task_id} no encontrada"}

    now = datetime.now().isoformat()
    new_pct = task["progress_pct"] if progress_pct is None else max(0, min(100, int(progress_pct)))
    new_step = task["current_step"] if current_step is None else current_step.strip()

    # Si llega al 100% y aún no estaba completada, cerrar automáticamente con el protocolo completo
    if new_pct >= 100 and task["status"] != "completed":
        conn.close()
        note_part = f" · {note.strip()[:80]}" if note and note.strip() else ""
        log_activity("PROGRESO", f"📊 #{task_id} ({author}) [100%] {new_step}{note_part} -> Disparando cierre automático")
        from app.services.milestone_checker import check_and_complete_task
        final_comment = (note.strip() if note and note.strip() else "") or new_step or "Tarea completada al 100%."
        res = check_and_complete_task(
            task_id=task_id,
            comment=final_comment,
            force_status="completed"
        )
        return {
            "success": True,
            "task_id": task_id,
            "status": "completed",
            "progress_pct": 100,
            "current_step": "✅ Completada y verificada con protocolo",
            "auto_completed": True,
            "protocol": res.get("protocol", {})
        }

    new_status = "in_progress" if task["status"] == "pending" and new_pct > 0 else task["status"]

    # Procesar y notificar hito intermedio a Telegram si corresponde
    detected_stage = normalize_stage(stage, new_pct) or normalize_stage(new_step, new_pct)
    raw_stages = task["notified_stages"] if "notified_stages" in task.keys() and task["notified_stages"] else ""
    notified_set = set(s.strip() for s in raw_stages.split(",") if s.strip())
    telegram_sent = False

    if detected_stage and detected_stage not in notified_set:
        should_notify = notify_telegram if notify_telegram is not None else True
        if should_notify:
            try:
                if detected_stage == "started":
                    from app.services.telegram_service import notify_task_started
                    tg_res = notify_task_started(
                        project_name=task["project_name"],
                        task_title=task["title"],
                        task_id=task_id
                    )
                    telegram_sent = tg_res.get("success", False)
                else:
                    from app.services.telegram_service import notify_task_intermediate_stage
                    desc = (note.strip() if note and note.strip() else "") or new_step
                    tg_res = notify_task_intermediate_stage(
                        project_name=task["project_name"],
                        task_title=task["title"],
                        stage=detected_stage,
                        stage_description=desc,
                        task_id=task_id,
                        progress_pct=new_pct
                    )
                    telegram_sent = tg_res.get("success", False)
                log_activity("HITO", f"📱 Hito #{task_id} [{detected_stage}] notificado por Telegram (éxito={telegram_sent}).")
            except Exception as e:
                log_activity("HITO", f"⚠️ Error al notificar hito #{task_id} [{detected_stage}] a Telegram: {e}")

        notified_set.add(detected_stage)

    updated_notified_stages = ",".join(sorted(notified_set))

    cursor.execute("""
        UPDATE tasks
        SET status = ?,
            progress_pct = ?,
            current_step = ?,
            notified_stages = ?,
            launched_at = COALESCE(launched_at, ?)
        WHERE id = ?
    """, (new_status, new_pct, new_step, updated_notified_stages, now, task_id))

    if note and note.strip():
        cursor.execute("""
            INSERT INTO comments (task_id, author, text, created_at)
            VALUES (?, ?, ?, ?)
        """, (task_id, author, f"[{new_pct}%] {note.strip()}", now))

    conn.commit()
    conn.close()

    note_part = f" · {note.strip()[:80]}" if note and note.strip() else ""
    stage_part = f" [{detected_stage}]" if detected_stage else ""
    log_activity("PROGRESO", f"📊 #{task_id} ({author}) [{new_pct}%]{stage_part} {new_step}{note_part}")
    sync_execution_queue_file()
    return {
        "success": True,
        "task_id": task_id,
        "status": new_status,
        "progress_pct": new_pct,
        "current_step": new_step,
        "stage": detected_stage,
        "telegram_notified": telegram_sent
    }


def get_next_global_queue_tasks(exclude_task_id: Optional[int] = None, limit: int = 5) -> Dict[str, Any]:
    """
    Obtiene las próximas tareas en la Cola Global ('in_progress')
    ordenadas por la secuencia de ejecución global (queue_order),
    excluyendo opcionalmente una tarea (por ejemplo la recién completada).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    params: List[Any] = []
    where_clause = "WHERE t.status = 'in_progress'"
    if exclude_task_id is not None:
        where_clause += " AND t.id != ?"
        params.append(exclude_task_id)

    query = f"""
        SELECT t.id, t.title, t.priority, t.progress_pct, t.current_step,
               COALESCE(t.queue_order, 0) as queue_order,
               p.name as project_name, p.folder_name, p.icon as project_icon
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        {where_clause}
        {QUEUE_ORDER_SQL}
    """
    cursor.execute(query, tuple(params))
    all_queue = [dict(r) for r in cursor.fetchall()]

    total_in_queue = len(all_queue)
    tasks_to_show = all_queue[:limit] if (limit and limit > 0) else all_queue

    cursor.execute("SELECT COUNT(*) as total FROM tasks WHERE status = 'pending'")
    total_pending = cursor.fetchone()["total"]
    conn.close()

    return {
        "tasks": tasks_to_show,
        "total_in_queue": total_in_queue,
        "total_pending": total_pending
    }


def get_launched_queue(project_id: Optional[str] = None) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    _normalize_queue_orders(cursor)
    conn.commit()

    query = """
        SELECT t.*, p.name as project_name, p.folder_name, p.folder_path, p.icon as project_icon, p.color as project_color
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.status = 'in_progress'
    """
    params: List[Any] = []
    if project_id:
        query += " AND t.project_id = ?"
        params.append(project_id)

    query += QUEUE_ORDER_SQL
    cursor.execute(query, tuple(params))
    tasks = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) as total FROM tasks WHERE status = 'in_progress'")
    total_global = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM tasks WHERE status = 'pending'")
    total_pending = cursor.fetchone()["total"]
    conn.close()

    # Incluir estado en vivo del Watchdog (trabajando vs esperando) + secuencia de motores
    watchdog_info = {}
    try:
        from app.services.watchdog_service import get_watchdog_status
        watchdog_info = get_watchdog_status()
    except Exception:
        pass

    if not tasks:
        master_prompt = ""
    else:
        lines = [
            "Mira, ponte a ejecutar en este orden exacto estas tareas de la Cola Global del Robot de Gestión de Proyectos:\n"
        ]
        for idx, t in enumerate(tasks, 1):
            target_info = f" | Target: `{t['milestone_target']}`" if t.get("milestone_target") else ""
            lines.append(
                f"{idx}. **[{t['project_name']}]** (`{t['folder_name']}`) — **{t['title']}** (ID `{t['id']}`)\n"
                f"   - Descripción: {t['description'] or 'Implementar funcionalidad solicitada.'}\n"
                f"   - Criterio de éxito: {t['milestone_description'] or 'Validación funcional completa.'}{target_info}"
            )

        models_seq = watchdog_info.get("models", [])
        seq_str = " → ".join([f"#{m['order']} {m['name']} ({m['quota_remaining_pct']}%)" for m in models_seq]) if models_seq else "Flash → Argon → Flash Lite"
        lines.append(
            f"\n🤖 **Estrategia de Motores & Autonomía:** Secuencia configurada: {seq_str}.\n"
            "- Para maximizar el tiempo de trabajo sin agotar cuota principal, delega subtareas mecánicas/de lectura en subagentes `flash` o `flash_lite` cuando proceda.\n"
            "- Mientras avanzas, ve actualizando el progreso de cada tarea en el Robot "
            "(`PATCH http://127.0.0.1:8002/api/tasks/{id}/progress`) y cuando termines cada una ciérrala "
            "(`POST http://127.0.0.1:8002/api/tasks/{id}/check`) para ejecutar la revisión general (Docs, OneNote, Git, Skills y Telegram)."
        )
        master_prompt = "\n\n".join(lines)

    runner_info = {}
    try:
        from app.services.queue_runner import get_runner_status
        runner_info = get_runner_status()
    except Exception:
        pass

    return {
        "success": True,
        "count": len(tasks),
        "total_global": total_global,
        "total_pending": total_pending,
        "watchdog": watchdog_info,
        "runner": runner_info,
        "tasks": tasks,
        "master_prompt": master_prompt,
        "queue_file": QUEUE_FILE
    }
