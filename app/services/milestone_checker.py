import os
import subprocess
import urllib.request
from datetime import datetime
from typing import Dict, Any, Optional
from app.database import get_db_connection
from app.services.telegram_service import notify_task_milestone

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

    m_type = task["milestone_type"]
    m_target = task["milestone_target"]
    is_success = True
    validation_message = ""

    # Si se fuerza el estado (por ejemplo, check interactivo en UI)
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

    protocol_res = {}
    # Si se ha completado la tarea, ejecutar el protocolo general automatizado
    if new_status == "completed":
        try:
            from app.services.task_protocol import execute_automated_task_completion_protocol
            protocol_res = execute_automated_task_completion_protocol(dict(task), result_text, image_path)
        except Exception as e:
            protocol_res = {"error": str(e), "protocol_summary": f"Error en protocolo automatizado: {e}"}

    # Actualizar tarea
    cursor.execute("""
        UPDATE tasks
        SET status = ?,
            milestone_result = ?,
            result_image_url = COALESCE(?, result_image_url),
            completed_at = CASE WHEN ? = 'completed' THEN ? ELSE NULL END
        WHERE id = ?
    """, (new_status, result_text, image_path, new_status, now, task_id))

    # Añadir comentario a la bitácora
    cursor.execute("""
        INSERT INTO comments (task_id, author, text, image_url, created_at)
        VALUES (?, 'Robot Organizador', ?, COALESCE(?, ''), ?)
    """, (task_id, result_text, image_path, now))

    # Si se ejecutó el protocolo, añadirlo también como comentario oficial
    if protocol_res.get("protocol_summary"):
        cursor.execute("""
            INSERT INTO comments (task_id, author, text, image_url, created_at)
            VALUES (?, 'Protocolo General', ?, '', ?)
        """, (task_id, protocol_res["protocol_summary"], now))

    conn.commit()
    conn.close()

    # Si se ha completado con éxito, enviar notificación a Telegram incluyendo el protocolo
    tg_result = {}
    if new_status == "completed":
        tg_comment = result_text
        if protocol_res.get("protocol_summary"):
            tg_comment += f"\n\n{protocol_res['protocol_summary']}"

        tg_result = notify_task_milestone(
            project_name=task["project_name"],
            task_title=task["title"],
            milestone_comment=tg_comment,
            image_path=image_path
        )

    return {
        "success": True,
        "task_id": task_id,
        "new_status": new_status,
        "is_success": is_success,
        "message": result_text,
        "protocol": protocol_res,
        "telegram_sent": tg_result.get("success", False)
    }
