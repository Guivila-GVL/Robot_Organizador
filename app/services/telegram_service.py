import os
import json
import html
import logging
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List
from app.database import get_db_connection

logger = logging.getLogger("telegram_service")

def get_setting(key: str, default: str = "") -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def send_telegram_message(text: str, parse_mode: str = "HTML") -> Dict[str, Any]:
    bot_token = get_setting("telegram_bot_token", "8691202872:AAGolw9n9HOGSos7NTlYHZJg-AeW4cMNzgU")
    chat_id = get_setting("telegram_chat_id", "7156474626")

    if not bot_token or not chat_id:
        return {"success": False, "error": "Bot token o Chat ID no configurados"}

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }

    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return {"success": True, "result": res_data}
    except Exception as e:
        logger.error(f"Error al enviar mensaje por Telegram: {e}")
        return {"success": False, "error": str(e)}

def send_telegram_photo(photo_path: str, caption: str = "", parse_mode: str = "HTML") -> Dict[str, Any]:
    bot_token = get_setting("telegram_bot_token", "8691202872:AAGolw9n9HOGSos7NTlYHZJg-AeW4cMNzgU")
    chat_id = get_setting("telegram_chat_id", "7156474626")

    if not bot_token or not chat_id:
        return {"success": False, "error": "Bot token o Chat ID no configurados"}

    if not os.path.exists(photo_path):
        # Fallback to text message if photo doesn't exist
        return send_telegram_message(f"{caption}\n\n<i>(Imagen adjunta no encontrada en disco: {os.path.basename(photo_path)})</i>", parse_mode)

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    boundary = "----WebKitFormBoundaryRobotOrganizador7MA4YWxkTrZu0gW"
    
    try:
        # El límite de caption en sendPhoto de Telegram es de 1024 caracteres
        send_full_text_separately = False
        photo_caption = caption
        if caption and len(caption) > 1024:
            photo_caption = caption[:1000] + "..."
            send_full_text_separately = True

        filename = os.path.basename(photo_path)
        with open(photo_path, "rb") as f:
            file_bytes = f.read()

        parts = []
        # chat_id
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))
        # caption
        if photo_caption:
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{photo_caption}\r\n".encode("utf-8"))
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\n{parse_mode}\r\n".encode("utf-8"))
        # photo file
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{filename}\"\r\nContent-Type: image/jpeg\r\n\r\n".encode("utf-8"))
        parts.append(file_bytes)
        parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        body = b"".join(parts)
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            # Si el caption era muy largo, enviamos el texto íntegro en un mensaje subsiguiente
            if send_full_text_separately:
                send_telegram_message(caption, parse_mode=parse_mode)
            return {"success": True, "result": res_data}
    except Exception as e:
        logger.error(f"Error al enviar foto por Telegram: {e}")
        # Si falla el envío de la foto, enviamos al menos el mensaje de texto
        text_fallback = f"{caption}\n\n<i>(Nota: No se pudo subir la imagen por error de red: {e})</i>"
        return send_telegram_message(text_fallback, parse_mode)

def trigger_n8n_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    n8n_url = get_setting("n8n_webhook_url", "http://localhost:5678/webhook/robot-task-completed")
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(n8n_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            return {"success": True, "status": response.status}
    except Exception as e:
        logger.warning(f"Webhook n8n no disponible o no configurado aún ({e}).")
        return {"success": False, "error": str(e)}

def format_queue_for_telegram(queue_data: Dict[str, Any]) -> str:
    """
    Genera el bloque HTML formateado para Telegram con las tareas en la Cola Global.
    Permite saber de un vistazo cuál es la siguiente tarea a trabajar.
    """
    tasks = queue_data.get("tasks", [])
    total_in_queue = queue_data.get("total_in_queue", 0)
    total_pending = queue_data.get("total_pending", 0)

    if not tasks or total_in_queue == 0:
        if total_pending > 0:
            return (
                "🎯 <b>Cola Global de Ejecución:</b>\n"
                f"✅ <i>Secuencia actual finalizada ({total_pending} tareas pendientes en backlog). Pulsa ▶️ Lanzar Tarea para añadir más a la cola.</i>"
            )
        else:
            return (
                "🎯 <b>Cola Global de Ejecución:</b>\n"
                "🎉 <i>¡Todas las tareas completadas! No quedan tareas pendientes en ningún proyecto.</i>"
            )

    header = "🚀 <b>Continuando automáticamente con la siguiente tarea:</b>" if total_in_queue == 1 else f"🚀 <b>Secuencia en marcha — Continuando automáticamente ({total_in_queue} en cola):</b>"
    lines = [header]

    for idx, t in enumerate(tasks, 1):
        safe_proj = html.escape(t.get("project_name") or "Proyecto", quote=False)
        safe_title = html.escape(t.get("title") or "", quote=False)
        icon = "▶️" if idx == 1 else "⏳"
        p_badge = ""
        p_val = (t.get("priority") or "").lower()
        if p_val == "alta":
            p_badge = " 🔥"

        lines.append(f"{icon} <b>#{idx} [{safe_proj}]</b> {safe_title}{p_badge} <i>(ID #{t['id']})</i>")

    remaining = total_in_queue - len(tasks)
    if remaining > 0:
        lines.append(f"<i>... y {remaining} tarea{'s' if remaining > 1 else ''} más en cola global</i>")

    return "\n".join(lines)

def notify_task_milestone(
    project_name: str,
    task_title: str,
    milestone_comment: str,
    image_path: Optional[str] = None,
    completed_task_id: Optional[int] = None,
    next_tasks: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    enabled = get_setting("notify_telegram_enabled", "true").lower() == "true"
    if not enabled:
        return {"success": True, "message": "Notificaciones desactivadas"}

    use_n8n = get_setting("notify_via_n8n", "false").lower() == "true"

    # Obtener las siguientes tareas de la Cola Global si no vienen pasadas explícitamente
    if next_tasks is not None:
        queue_data = {
            "tasks": next_tasks,
            "total_in_queue": len(next_tasks),
            "total_pending": 0
        }
    else:
        try:
            from app.services.execution_queue import get_next_global_queue_tasks
            queue_data = get_next_global_queue_tasks(exclude_task_id=completed_task_id, limit=4)
        except Exception as e:
            logger.warning(f"No se pudo consultar la Cola Global para el reporte Telegram: {e}")
            queue_data = {"tasks": [], "total_in_queue": 0, "total_pending": 0}

    queue_section = format_queue_for_telegram(queue_data)

    safe_project = html.escape(project_name, quote=False)
    safe_title = html.escape(task_title, quote=False)

    caption = (
        f"✅ <b>Hito Completado: {safe_project}</b>\n\n"
        f"📌 <b>Tarea:</b> {safe_title}\n"
        f"💬 <b>Resultado:</b>\n{milestone_comment}\n\n"
        f"{queue_section}\n\n"
        f"⏱ <i>Robot Organizador 2026</i>"
    )

    result = {}
    if use_n8n:
        payload = {
            "project": project_name,
            "task": task_title,
            "comment": milestone_comment,
            "image_path": image_path,
            "caption": caption,
            "next_tasks": queue_data.get("tasks", []),
            "total_in_queue": queue_data.get("total_in_queue", 0),
            "total_pending": queue_data.get("total_pending", 0)
        }
        result = trigger_n8n_webhook(payload)
        # Si n8n falla o no está respondiendo, hacemos fallback directo a Telegram
        if not result.get("success"):
            if image_path and os.path.exists(image_path):
                return send_telegram_photo(image_path, caption)
            else:
                return send_telegram_message(caption)
        return result

    # Envío directo por Telegram
    if image_path and os.path.exists(image_path):
        return send_telegram_photo(image_path, caption)
    else:
        return send_telegram_message(caption)
