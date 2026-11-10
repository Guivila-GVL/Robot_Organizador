import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.database import get_db_connection

WORKSPACE_ROOT = r"D:\OneDrive\04_Desarrollo_proyectos"
QUEUE_FILE = os.path.join(WORKSPACE_ROOT, "0000_Utilidades", "COLA_EJECUCION_ANTIGRAVITY.md")


def sync_execution_queue_file() -> str:
    """Sincroniza todas las tareas en estado 'in_progress' a un archivo legible para cualquier agente."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, p.name as project_name, p.folder_name, p.folder_path
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.status = 'in_progress'
        ORDER BY
            CASE t.priority
                WHEN 'urgente' THEN 1
                WHEN 'alta' THEN 2
                WHEN 'media' THEN 3
                ELSE 4
            END ASC,
            t.launched_at ASC,
            t.id ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    lines = [
        "# 🚀 Cola Activa de Tareas Lanzadas (Antigravity IDE)",
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
                f"## {idx}. [{t['project_name']}] {t['title']} (ID `{t['id']}`)",
                f"- **Proyecto / Carpeta:** `{t['folder_path']}`",
                f"- **Prioridad:** {t['priority'].upper()} | **Progreso:** `{pct}%` — *{step}*",
                f"- **Descripción:** {t['description'] or 'Sin descripción adicional'}",
                f"- **Criterio de éxito ({t['milestone_type']}):** {t['milestone_description'] or t['milestone_target'] or 'Validación técnica estándar'}",
                ""
            ])

    lines.extend([
        "---",
        "### 📡 Instrucciones para el Agente (Tracking en Vivo + Cierre):",
        "1. Para reportar progreso mientras trabajas en una tarea:",
        "   `PATCH http://127.0.0.1:8002/api/tasks/{id}/progress` con `{\"progress_pct\": 50, \"current_step\": \"Implementando...\", \"note\": \"...\"}`",
        "2. Al terminar y validar la tarea, ciérrala llamando a:",
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

    cursor.execute("""
        UPDATE tasks
        SET status = 'in_progress',
            progress_pct = ?,
            current_step = ?,
            launched_at = COALESCE(launched_at, ?)
        WHERE id = ?
    """, (new_pct, step_text, now, task_id))

    cursor.execute("""
        INSERT INTO comments (task_id, author, text, created_at)
        VALUES (?, 'Sistema', ?, ?)
    """, (task_id, "🚀 Tarea lanzada a 'En Progreso' y añadida a la cola de ejecución.", now))

    conn.commit()
    conn.close()

    queue_path = sync_execution_queue_file()
    return {
        "success": True,
        "task_id": task_id,
        "status": "in_progress",
        "progress_pct": new_pct,
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
            current_step = ?
        WHERE id = ?
    """, (step_text, task_id))

    cursor.execute("""
        INSERT INTO comments (task_id, author, text, created_at)
        VALUES (?, 'Sistema', ?, ?)
    """, (task_id, "⏸️ Tarea pausada y devuelta a la lista de Pendientes.", now))

    conn.commit()
    conn.close()

    sync_execution_queue_file()
    return {"success": True, "task_id": task_id, "status": "pending"}


def update_task_progress(
    task_id: int,
    progress_pct: Optional[int] = None,
    current_step: Optional[str] = None,
    note: Optional[str] = None,
    author: str = "Agente"
) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return {"success": False, "error": f"Tarea {task_id} no encontrada"}

    now = datetime.now().isoformat()
    new_pct = task["progress_pct"] if progress_pct is None else max(0, min(100, int(progress_pct)))
    new_step = task["current_step"] if current_step is None else current_step.strip()

    # Si estaba pendiente y se reporta avance, pasarla a en progreso automáticamente
    new_status = "in_progress" if task["status"] == "pending" and new_pct > 0 else task["status"]

    cursor.execute("""
        UPDATE tasks
        SET status = ?,
            progress_pct = ?,
            current_step = ?,
            launched_at = COALESCE(launched_at, ?)
        WHERE id = ?
    """, (new_status, new_pct, new_step, now, task_id))

    if note and note.strip():
        cursor.execute("""
            INSERT INTO comments (task_id, author, text, created_at)
            VALUES (?, ?, ?, ?)
        """, (task_id, author, f"[{new_pct}%] {note.strip()}", now))

    conn.commit()
    conn.close()

    sync_execution_queue_file()
    return {
        "success": True,
        "task_id": task_id,
        "status": new_status,
        "progress_pct": new_pct,
        "current_step": new_step
    }


def get_launched_queue(project_id: Optional[str] = None) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT t.*, p.name as project_name, p.folder_name, p.folder_path, p.icon as project_icon
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.status = 'in_progress'
    """
    params: List[Any] = []
    if project_id:
        query += " AND t.project_id = ?"
        params.append(project_id)

    query += """
        ORDER BY
            CASE t.priority
                WHEN 'urgente' THEN 1
                WHEN 'alta' THEN 2
                WHEN 'media' THEN 3
                ELSE 4
            END ASC,
            t.launched_at ASC,
            t.id ASC
    """
    cursor.execute(query, tuple(params))
    tasks = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) as total FROM tasks WHERE status = 'in_progress'")
    total_global = cursor.fetchone()["total"]
    conn.close()

    if not tasks:
        master_prompt = ""
    else:
        lines = [
            "Mira, ponte a ejecutar estas tareas que acabo de lanzar en el Robot de Gestión de Proyectos:\n"
        ]
        for idx, t in enumerate(tasks, 1):
            target_info = f" | Target: `{t['milestone_target']}`" if t.get("milestone_target") else ""
            lines.append(
                f"{idx}. **{t['project_name']}** (`{t['folder_name']}`) — **{t['title']}** (ID `{t['id']}`)\n"
                f"   - Descripción: {t['description'] or 'Implementar funcionalidad solicitada.'}\n"
                f"   - Criterio de éxito: {t['milestone_description'] or 'Validación funcional completa.'}{target_info}"
            )
        lines.append(
            "\nMientras avanzas, ve actualizando el progreso de cada tarea en el Robot "
            "(`PATCH http://127.0.0.1:8002/api/tasks/{id}/progress`) y cuando termines cada una ciérrala "
            "(`POST http://127.0.0.1:8002/api/tasks/{id}/check`) para ejecutar la revisión general (Docs, OneNote, Git, Skills y Telegram)."
        )
        master_prompt = "\n\n".join(lines)

    return {
        "success": True,
        "count": len(tasks),
        "total_global": total_global,
        "tasks": tasks,
        "master_prompt": master_prompt,
        "queue_file": QUEUE_FILE
    }

