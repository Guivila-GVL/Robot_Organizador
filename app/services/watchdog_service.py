import os
import re
import json
import glob
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from app.database import get_db_connection
from app.services.telegram_service import send_telegram_message

BRAIN_DIR = os.path.expanduser(r"~\.gemini\antigravity\brain")

# Ventana estándar de renovación de cuota (5 horas) y presupuesto estimado de pasos del modelo por ventana
QUOTA_WINDOW_HOURS = 5
DEFAULT_WINDOW_STEP_BUDGET = 120

_last_alerted_quota_key: Optional[str] = None

QUOTA_KEYWORDS = [
    "resource_exhausted",
    "quota exceeded",
    "rate limit",
    "429 too many requests",
    "http 429",
    "exhausted your capacity"
]


def _find_recent_transcripts(max_files: int = 5) -> List[str]:
    if not os.path.exists(BRAIN_DIR):
        return []

    pattern = os.path.join(BRAIN_DIR, "*", ".system_generated", "logs", "transcript.jsonl")
    candidates = glob.glob(pattern)
    if not candidates:
        return []

    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[:max_files]


def _read_jsonl_lines(filepath: str, max_bytes: int = 262144) -> List[Dict[str, Any]]:
    try:
        with open(filepath, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block_size = min(size, max_bytes)
            f.seek(size - block_size)
            data = f.read().decode("utf-8", errors="ignore")
        lines = [ln.strip() for ln in data.splitlines() if ln.strip()]
        parsed = []
        for ln in lines:
            try:
                parsed.append(json.loads(ln))
            except Exception:
                continue
        return parsed
    except Exception:
        return []


def _parse_iso_utc(ts_str: str) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str).astimezone(timezone.utc)
    except Exception:
        return None


def _compute_quota_metrics(transcripts: List[str], quota_error_active: bool) -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    window_start_cutoff = now_utc - timedelta(hours=QUOTA_WINDOW_HOURS)

    active_model = "Gemini (Auto)"
    model_steps: Dict[str, List[datetime]] = {}

    # Recorrer del más antiguo al más reciente para seguir qué modelo estaba activo en cada paso
    for idx in range(len(transcripts) - 1, -1, -1):
        tpath = transcripts[idx]
        mtime_utc = datetime.fromtimestamp(os.path.getmtime(tpath), tz=timezone.utc)
        if idx > 0 and mtime_utc < window_start_cutoff:
            continue

        entries = _read_jsonl_lines(tpath, max_bytes=400000)
        current_conv_model = active_model
        for e in entries:
            if e.get("type") == "USER_INPUT":
                content = e.get("content", "")
                m = re.search(r"changed setting `Model Selection` from .*? to ([^\.\n]+)", content)
                if m:
                    current_conv_model = m.group(1).strip()
                    if idx == 0:
                        active_model = current_conv_model

            if e.get("type") == "PLANNER_RESPONSE":
                dt = _parse_iso_utc(e.get("created_at", ""))
                if dt and dt >= window_start_cutoff:
                    model_steps.setdefault(current_conv_model, []).append(dt)

    planner_timestamps = sorted(model_steps.get(active_model, []))
    steps_used = len(planner_timestamps)

    if quota_error_active:
        remaining_pct = 0
    else:
        used_ratio = min(1.0, steps_used / float(DEFAULT_WINDOW_STEP_BUDGET))
        remaining_pct = max(0, int(round((1.0 - used_ratio) * 100)))

    # Color según umbrales: > 50% verde, 20%-50% naranja, < 20% rojo
    if remaining_pct < 20:
        color = "red"
    elif remaining_pct <= 50:
        color = "orange"
    else:
        color = "green"

    # Calcular tiempo hasta la renovación del ciclo de 5h
    if planner_timestamps:
        oldest_in_window = planner_timestamps[0]
        reset_at_utc = oldest_in_window + timedelta(hours=QUOTA_WINDOW_HOURS)
        remaining_secs = max(0, int((reset_at_utc - now_utc).total_seconds()))
        hours = remaining_secs // 3600
        mins = (remaining_secs % 3600) // 60
        reset_local = reset_at_utc.astimezone()
        reset_clock = reset_local.strftime("%H:%M")
        if hours > 0:
            reset_text = f"Renueva en {hours}h {mins:02d}m ({reset_clock})"
        else:
            reset_text = f"Renueva en {mins}m ({reset_clock})"
    else:
        remaining_secs = 0
        reset_text = "Cuota completa · Sin espera"

    return {
        "quota_remaining_pct": remaining_pct,
        "quota_color": color,
        "steps_used": steps_used,
        "steps_budget": DEFAULT_WINDOW_STEP_BUDGET,
        "reset_in_seconds": remaining_secs,
        "reset_text": reset_text,
        "active_model": active_model
    }


def get_watchdog_status() -> Dict[str, Any]:
    global _last_alerted_quota_key

    transcripts = _find_recent_transcripts()
    if not transcripts:
        return {
            "active": False,
            "state": "idle",
            "label": "Sin sesión detectada",
            "detail": "No se encontró transcript.jsonl",
            "conversation_id": None,
            "quota_alert": False,
            "quota_remaining_pct": 100,
            "quota_color": "green",
            "reset_text": "Cuota al 100%",
            "active_model": "Gemini"
        }

    transcript_path = transcripts[0]
    parts = os.path.normpath(transcript_path).split(os.sep)
    conv_id = parts[-4] if len(parts) >= 4 else "desconocido"

    mtime = os.path.getmtime(transcript_path)
    age_seconds = max(0, int(datetime.now().timestamp() - mtime))
    entries = _read_jsonl_lines(transcript_path, max_bytes=65536)

    if not entries:
        quota_info = _compute_quota_metrics(transcripts, False)
        return {
            "active": True,
            "state": "idle",
            "label": "Esperando órdenes",
            "detail": f"Sesión {conv_id[:8]}...",
            "conversation_id": conv_id,
            "age_seconds": age_seconds,
            "quota_alert": False,
            **quota_info
        }

    last_entry = entries[-1]
    step_index = last_entry.get("step_index", 0)
    step_type = last_entry.get("type", "")
    step_status = last_entry.get("status", "")

    # Comprobar si en los últimos pasos hay un error de cuota 429
    quota_detected = False
    for entry in reversed(entries[-3:]):
        raw_dump = json.dumps(entry, ensure_ascii=False).lower()
        if entry.get("status") == "ERROR" or any(k in raw_dump for k in QUOTA_KEYWORDS):
            if any(k in raw_dump for k in QUOTA_KEYWORDS):
                quota_detected = True
                break

    quota_info = _compute_quota_metrics(transcripts, quota_detected)

    if quota_detected:
        alert_key = f"{conv_id}:{step_index}"
        if _last_alerted_quota_key != alert_key:
            _last_alerted_quota_key = alert_key
            try:
                send_telegram_message(
                    "⚠️ <b>Watchdog Antigravity: Cuota Agotada (429)</b>\n\n"
                    f"🆔 <b>Sesión:</b> <code>{conv_id[:8]}</code>\n"
                    f"🤖 <b>Modelo:</b> {quota_info['active_model']}\n"
                    f"⏳ <b>Recarga:</b> {quota_info['reset_text']}\n"
                    f"💡 Cambia de modelo en Antigravity IDE para continuar."
                )
            except Exception:
                pass

        return {
            "active": True,
            "state": "quota_error",
            "label": "⚠️ Cuota Gemini agotada (429)",
            "detail": f"Paso #{step_index} · Cambia de modelo para continuar",
            "conversation_id": conv_id,
            "step_index": step_index,
            "age_seconds": age_seconds,
            "quota_alert": True,
            **quota_info
        }

    if age_seconds <= 25 and (step_status in ("IN_PROGRESS", "RUNNING") or step_type == "USER_INPUT"):
        label = f"⚡ Trabajando (Paso #{step_index})"
        state = "working"
    elif age_seconds <= 120:
        label = f"🟢 Activo · Esperando órdenes (#{step_index})"
        state = "ready"
    else:
        mins = age_seconds // 60
        label = f"🟢 En espera (hace {mins} min)"
        state = "idle"

    return {
        "active": True,
        "state": state,
        "label": label,
        "detail": f"Sesión {conv_id[:8]} · Modelo: {quota_info['active_model']} · Pasos ventana: {quota_info['steps_used']}/{quota_info['steps_budget']}",
        "conversation_id": conv_id,
        "step_index": step_index,
        "age_seconds": age_seconds,
        "quota_alert": False,
        **quota_info
    }


def build_agent_prompt_for_task(task_id: int) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, p.name as project_name, p.folder_name, p.folder_path
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.id = ?
    """, (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"success": False, "error": "Tarea no encontrada"}

    target_info = f"\n- Validación automática ({row['milestone_type']}): `{row['milestone_target']}`" if row["milestone_target"] else ""
    milestone_desc = row["milestone_description"] or "Funcionamiento validado y sin errores."

    prompt = (
        f"Vamos a ejecutar la siguiente tarea del proyecto **{row['project_name']}** (`{row['folder_name']}`):\n\n"
        f"### 🎯 Tarea: {row['title']}\n"
        f"- **Descripción:** {row['description'] or 'Implementar y verificar la funcionalidad indicada.'}\n"
        f"- **Prioridad:** {row['priority'].upper()}\n"
        f"- **Criterio de éxito esperado:** {milestone_desc}{target_info}\n\n"
        f"Al terminar, verifica el funcionamiento técnico y actualiza el estado de la tarea (ID `{row['id']}`) en el Robot Organizador."
    )

    return {
        "success": True,
        "task_id": row["id"],
        "title": row["title"],
        "prompt": prompt
    }
