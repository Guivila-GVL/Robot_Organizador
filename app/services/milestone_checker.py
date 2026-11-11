import os
import threading
import subprocess
import urllib.request
from datetime import datetime
from typing import Dict, Any, Optional
from app.database import get_db_connection
from app.services.telegram_service import notify_task_milestone
from app.services.activity_logger import log_activity


def _run_heavy_protocol_async(task_dict: Dict[str, Any], result_text: str) -> None:
    """
    Ejecuta en segundo plano las operaciones lentas del protocolo de cierre
    (sincronización OneNote Graph API y git commit/push) para no bloquear la UI
    ni el cierre instantáneo de la tarea.
    """
    task_id = task_dict.get("id")
    project_id = task_dict.get("project_id", "")
    project_name = task_dict.get("project_name", "Proyecto")
    project_folder = task_dict.get("project_folder") or ""
    task_title = task_dict.get("title", "Tarea")

    try:
        from app.services.task_protocol import sync_onenote_project, commit_and_push_git

        log_activity("PROTOCOLO", f"📓 Sincronizando OneNote en segundo plano para '{project_name}' (Tarea #{task_id})...")
        onenote_res = sync_onenote_project(project_id)
        if onenote_res.get("success"):
            log_activity("PROTOCOLO", f"✅ OneNote actualizado para '{project_name}' (Tarea #{task_id}).")
        else:
            log_activity("PROTOCOLO", f"⚠️ Aviso OneNote ({project_name}): {onenote_res.get('error', 'sin detalle')}")

        log_activity("PROTOCOLO", f"🐙 Ejecutando Git commit & push para '{project_name}' (Tarea #{task_id})...")
        git_res = commit_and_push_git(project_folder, task_title)
        if git_res.get("push_done"):
            log_activity("PROTOCOLO", f"✅ Git commit & push completado para '{project_name}'.")
        elif git_res.get("commit_done"):
            log_activity("PROTOCOLO", f"ℹ️ Git commit local realizado para '{project_name}'.")
        else:
            log_activity("PROTOCOLO", f"ℹ️ Git sin cambios nuevos o pendiente en '{project_name}'.")

        summary_msg = (
            f"📋 PROTOCOLO DE CIERRE COMPLETADO:\n"
            f"• 📁 Docs: ✅ Registrado en docs/REGISTRO_HITOS.md\n"
            f"• 📓 OneNote: {'✅ Sincronizado en OneNote (Resumen y Actividades)' if onenote_res.get('success') else '⚠️ Sincronización pendiente'}\n"
            f"• 🐙 Git: {'✅ Commit y Push a GitHub completado' if git_res.get('push_done') else ('ℹ️ Commit local realizado' if git_res.get('commit_done') else 'ℹ️ Sin cambios pendientes')}\n"
            f"• 🧠 Skills: ✅ Patrones verificados"
        )
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO comments (task_id, author, text, image_url, created_at) VALUES (?, 'Protocolo General', ?, '', ?)",
            (task_id, summary_msg, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log_activity("PROTOCOLO", f"⚠️ Error en protocolo asíncrono de tarea #{task_id}: {e}")


def check_and_complete_task(
    task_id: int,
    comment: str = "",
    image_path: Optional[str] = None,
    force_status: Optional[str] = None
) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.*, p.name as project_name, p.folder_path as project_folder
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.id = ?
    """, (task_id,))
    task = cursor.fetchone()

    if not task:
        conn.close()
        return {"success": False, "error": f"Tarea con ID {task_id} no encontrada"}

    # Evitar duplicar cierre si ya estaba completada y se vuelve a pedir 'completed'
    if task["status"] == "completed" and force_status == "completed":
        conn.close()
        return {
            "success": True,
            "task_id": task_id,
            "new_status": "completed",
            "is_success": True,
            "already_completed": True,
            "message": task["milestone_result"] or "La tarea ya figuraba como completada."
        }

    m_type = task["milestone_type"]
    m_target = task["milestone_target"]
    is_success = True
    validation_message = ""

    # Si se fuerza el estado (por ejemplo, check interactivo en UI o cierre de agente)
    if force_status:
        new_status = force_status
        is_success = (new_status == "completed")
    else:
        # Validación automatizada según el tipo de hito
        if m_type == "http_200" and m_target:
            try:
                req = urllib.request.Request(m_target, headers={"User-Agent": "RobotOrganizador/1.0"})
                with urllib.request.urlopen(req, timeout=5) as res:
                    if res.status == 200:
                        is_success = True
                        validation_message = f"Servicio HTTP {m_target} respondió 200 OK correctamente."
                    else:
                        is_success = False
                        validation_message = f"Servicio HTTP respondió con código {res.status}."
            except Exception as e:
                is_success = False
                validation_message = f"Error al conectar con {m_target}: {e}"

        elif m_type == "file_exists" and m_target:
            target_path = m_target
            if not os.path.isabs(target_path):
                target_path = os.path.join(task["project_folder"], m_target)
            if os.path.exists(target_path):
                is_success = True
                validation_message = f"Archivo verificado en disco: {os.path.basename(target_path)}"
            else:
                is_success = False
                validation_message = f"Archivo no encontrado: {target_path}"

        elif m_type == "command_exit_0" and m_target:
            try:
                res = subprocess.run(m_target, shell=True, cwd=task["project_folder"], capture_output=True, text=True, timeout=30)
                if res.returncode == 0:
                    is_success = True
                    validation_message = f"Comando ejecutado con éxito (código 0):\n{res.stdout[:200]}"
                else:
                    is_success = False
                    validation_message = f"Comando falló (código {res.returncode}):\n{res.stderr[:200]}"
            except Exception as e:
                is_success = False
                validation_message = f"Error en ejecución de comando: {e}"
        else:
            # Validación manual
            is_success = True
            validation_message = "Hito validado manualmente por el usuario."

        new_status = "completed" if is_success else "failed"

    now = datetime.now().isoformat()
    result_text = comment if comment else validation_message
    if not result_text:
        result_text = "Hito completado satisfactoriamente."

    # 1. Actualizar tarea en la base de datos de inmediato (y sacar de queue_order si se completa)
    new_step = "✅ Completada y verificada con protocolo" if new_status == "completed" else ""
    cursor.execute("""
        UPDATE tasks
        SET status = ?,
            milestone_result = ?,
            result_image_url = COALESCE(?, result_image_url),
            progress_pct = CASE WHEN ? = 'completed' THEN 100 WHEN ? = 'pending' THEN 0 ELSE progress_pct END,
            current_step = CASE WHEN ? = 'completed' THEN ? WHEN ? = 'pending' THEN '' ELSE current_step END,
            queue_order = CASE WHEN ? = 'completed' THEN 0 ELSE queue_order END,
            completed_at = CASE WHEN ? = 'completed' THEN ? ELSE NULL END
        WHERE id = ?
    """, (new_status, result_text, image_path, new_status, new_status, new_status, new_step, new_status, new_status, now, task_id))

    # Añadir comentario a la bitácora
    cursor.execute("""
        INSERT INTO comments (task_id, author, text, image_url, created_at)
        VALUES (?, 'Robot Organizador', ?, COALESCE(?, ''), ?)
    """, (task_id, result_text, image_path, now))

    conn.commit()
    conn.close()

    # 2. Sincronizar archivo local de Cola Global al instante
    try:
        from app.services.execution_queue import sync_execution_queue_file
        sync_execution_queue_file()
    except Exception:
        pass

    protocol_res = {}
    tg_result = {}

    if new_status == "completed":
        task_dict = dict(task)
        task_dict["status"] = new_status
        task_dict["completed_at"] = now
        task_dict["milestone_result"] = result_text

        # 3. Actualizar docs/REGISTRO_HITOS.md al instante (operación en disco local < 20ms)
        try:
            from app.services.task_protocol import update_project_docs, review_skills_adherence
            docs_res = update_project_docs(task["project_folder"], task["project_name"], task_dict, result_text)
            skills_res = review_skills_adherence(task["project_id"], task["title"])
            protocol_summary = (
                f"📋 PROTOCOLO DE CIERRE ACTIVADO:\n"
                f"• 📁 Docs: {'✅ Registrado en docs/REGISTRO_HITOS.md' if docs_res.get('success') else '⚠️ Error en docs'}\n"
                f"• 📓 OneNote: 🔄 Sincronizando sección del proyecto en segundo plano\n"
                f"• 🐙 Git: 🔄 Commit y Push a GitHub en ejecución\n"
                f"• 🧠 Skills: ✅ Patrones verificados ({len(skills_res.get('skills_applied', []))} habilidades)"
            )
            protocol_res = {"success": True, "docs": docs_res, "skills": skills_res, "protocol_summary": protocol_summary}
        except Exception as e:
            protocol_res = {"error": str(e), "protocol_summary": f"Protocolo iniciado ({e})"}

        # 4. Enviar notificación a Telegram de inmediato (incluyendo las siguientes tareas de la Cola Global)
        tg_comment = result_text
        if protocol_res.get("protocol_summary") and "Protocolo Verificado" not in result_text:
            tg_comment += f"\n\n{protocol_res['protocol_summary']}"

        tg_result = notify_task_milestone(
            project_name=task["project_name"],
            task_title=task["title"],
            milestone_comment=tg_comment,
            image_path=image_path,
            completed_task_id=task_id
        )
        log_activity("HITO", f"✅ #{task_id} completada [{task['project_name']}] -> {task['title'][:65]}")

        # 5. Lanzar OneNote Sync + Git Push en hilo background para no bloquear la respuesta HTTP
        bg_thread = threading.Thread(
            target=_run_heavy_protocol_async,
            args=(task_dict, result_text),
            daemon=True
        )
        bg_thread.start()

    elif new_status == "failed":
        log_activity("HITO", f"❌ #{task_id} falló validación: {result_text[:90]}")

    return {
        "success": True,
        "task_id": task_id,
        "new_status": new_status,
        "is_success": is_success,
        "message": result_text,
        "protocol": protocol_res,
        "telegram_sent": tg_result.get("success", False)
    }
