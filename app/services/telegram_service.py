import os
import json
import logging
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any
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
        filename = os.path.basename(photo_path)
        with open(photo_path, "rb") as f:
            file_bytes = f.read()

        parts = []
        # chat_id
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))
        # caption
        if caption:
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
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

def notify_task_milestone(
    project_name: str,
    task_title: str,
    milestone_comment: str,
    image_path: Optional[str] = None
) -> Dict[str, Any]:
    enabled = get_setting("notify_telegram_enabled", "true").lower() == "true"
    if not enabled:
        return {"success": True, "message": "Notificaciones desactivadas"}

    use_n8n = get_setting("notify_via_n8n", "false").lower() == "true"

    caption = (
        f"✅ <b>Hito Completado: {project_name}</b>\n\n"
        f"📌 <b>Tarea:</b> {task_title}\n"
        f"💬 <b>Resultado:</b>\n{milestone_comment}\n\n"
        f"⏱ <i>Robot Organizador 2026</i>"
    )

    result = {}
    if use_n8n:
        payload = {
            "project": project_name,
            "task": task_title,
            "comment": milestone_comment,
            "image_path": image_path,
            "caption": caption
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
