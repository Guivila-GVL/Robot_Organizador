import os
import re
import json
import glob
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from app.database import get_db_connection
from app.services.telegram_service import send_telegram_message, get_setting, set_setting

BRAIN_DIR = os.path.expanduser(r"~\.gemini\antigravity\brain")

QUOTA_WINDOW_HOURS = 5

# Catálogo oficial de motores verificados en Antigravity (`agy models`)
DEFAULT_MODELS_INFO = {
    "Gemini 3.8 Flash (Medium)": {
        "cli_id": "gemini-3.8-flash-medium",
        "budget": 450,
        "tier": "Gemini Flash · Rápido y Alta Autonomía"
    },
    "Claude Sonnet 5.5 (Medium)": {
        "cli_id": "claude-sonnet-5-5-medium",
        "budget": 160,
        "tier": "Claude Sonnet · Arquitectura y Código Preciso"
    },
    "Gemini 4 Argon (Medium)": {
        "cli_id": "gemini-4-argon-medium",
        "budget": 180,
        "tier": "Gemini Argon · Razonamiento Complejo"
    },
    "Claude Opus 5.5 (Medium)": {
        "cli_id": "claude-opus-5-5-medium",
        "budget": 100,
        "tier": "Claude Opus · Máxima Profundidad"
    },
    "Gemini 3.8 Flash (High)": {
        "cli_id": "gemini-3.8-flash-high",
        "budget": 400,
        "tier": "Gemini Flash High · Alta Capacidad"
    },
    "GPT-OSS 120B (Medium)": {
        "cli_id": "gpt-oss-120b-medium",
        "budget": 250,
        "tier": "GPT-OSS 120B · Respaldo Abierto"
    },
    "Gemini 3.8 Flash (Low)": {
        "cli_id": "gemini-3.8-flash-low",
        "budget": 600,
        "tier": "Flash Low · Última línea de autonomía"
    },
    "Gemini 3.5 Flash (High)": {
        "cli_id": "gemini-3.8-flash-high",
        "budget": 450,
        "tier": "Flash Respaldo · Alta Precisión"
    }
}

DEFAULT_FALLBACK_SEQUENCE = [
    "Gemini 3.8 Flash (Medium)",
    "Claude Sonnet 5.5 (Medium)",
    "Gemini 4 Argon (Medium)",
    "Claude Opus 5.5 (Medium)",
    "GPT-OSS 120B (Medium)",
    "Gemini 3.8 Flash (Low)"
]


def get_cli_id_for_model(model_name: str) -> str:
    if model_name in DEFAULT_MODELS_INFO:
        return DEFAULT_MODELS_INFO[model_name]["cli_id"]
    lower = model_name.lower()
    if "claude" in lower and "opus" in lower:
        return "claude-opus-5-5-medium"
    if "claude" in lower:
        return "claude-sonnet-5-5-medium"
    if "gpt" in lower:
        return "gpt-oss-120b-medium"
    if "argon" in lower:
        return "gemini-4-argon-medium"
    if "low" in lower or "lite" in lower:
        return "gemini-3.8-flash-low"
    return "gemini-3.8-flash-medium"

_last_alerted_quota_key: Optional[str] = None

QUOTA_KEYWORDS = [
    "resource_exhausted",
    "quota exceeded",
    "rate limit",
    "429 too many requests",
    "http 429",
    "exhausted your capacity"
]


def _estimate_budget_for_model(model_name: str) -> int:
    if model_name in DEFAULT_MODELS_INFO:
        return DEFAULT_MODELS_INFO[model_name]["budget"]
    lower = model_name.lower()
    if "lite" in lower:
        return 600
    if "flash" in lower:
        return 450
    if any(k in lower for k in ["argon", "pro", "ultra", "opus", "sonnet", "gpt-5"]):
        return 180
    return 300


def _describe_tier_for_model(model_name: str) -> str:
    if model_name in DEFAULT_MODELS_INFO:
        return DEFAULT_MODELS_INFO[model_name]["tier"]
    lower = model_name.lower()
    if "lite" in lower:
        return "Lite · Autonomía Máxima"
    if "flash" in lower:
        return "Flash · Velocidad y Cuota Amplia"
    if any(k in lower for k in ["argon", "pro", "opus"]):
        return "Pro / Avanzado · Tareas Complejas"
    return "Motor Antigravity"


def parse_reset_duration(text: str) -> Optional[timedelta]:
    """Extrae la duración exacta de renovación reportada por agy CLI o APIs (ej. 'Resets in 89h15m13s')."""
    if not text:
        return None
    m = re.search(
        r"resets?\s+in\s+(?:(\d+)\s*d(?:ays?)?\s*)?(?:(\d+)\s*h(?:ours?)?\s*)?(?:(\d+)\s*m(?:in(?:utes?)?)?\s*)?(?:(\d+)\s*s(?:ec(?:onds?)?)?)?",
        text,
        re.IGNORECASE
    )
    if m:
        days = int(m.group(1) or 0)
        hours = int(m.group(2) or 0)
        mins = int(m.group(3) or 0)
        secs = int(m.group(4) or 0)
        total_seconds = days * 86400 + hours * 3600 + mins * 60 + secs
        if total_seconds > 0:
            return timedelta(seconds=total_seconds)
    return None


def _find_recent_transcripts(max_files: int = 60, window_hours: int = QUOTA_WINDOW_HOURS) -> List[str]:
    search_dirs = [
        os.path.expanduser(r"~\.gemini\antigravity-cli\brain"),
        os.path.expanduser(r"~\.gemini\antigravity\brain")
    ]
    candidates = []
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(hours=window_hours + 1)).timestamp()
    for sdir in search_dirs:
        if os.path.exists(sdir):
            pattern = os.path.join(sdir, "*", ".system_generated", "logs", "transcript.jsonl")
            for p in glob.glob(pattern):
                try:
                    if os.path.getmtime(p) >= cutoff_ts:
                        candidates.append(p)
                except Exception:
                    pass

    if not candidates:
        for sdir in search_dirs:
            if os.path.exists(sdir):
                pattern = os.path.join(sdir, "*", ".system_generated", "logs", "transcript.jsonl")
                candidates.extend(glob.glob(pattern))

    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[:max_files]


def _read_jsonl_lines(filepath: str, max_bytes: int = 450000) -> List[Dict[str, Any]]:
    try:
        with open(filepath, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size <= max_bytes:
                f.seek(0)
                data = f.read().decode("utf-8", errors="ignore")
                all_raw = data.splitlines()
            else:
                # Leer primeros 16KB para asegurar inclusión del paso 0 (Model Selection)
                f.seek(0)
                head_data = f.read(16384).decode("utf-8", errors="ignore")
                head_lines = head_data.splitlines()
                # Leer el final para turnos recientes
                f.seek(size - max_bytes)
                tail_data = f.read().decode("utf-8", errors="ignore")
                tail_lines = tail_data.splitlines()
                all_raw = head_lines + tail_lines

        parsed = []
        seen_keys = set()
        for ln in all_raw:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
                k = (obj.get("step_index"), obj.get("type"), obj.get("created_at"))
                if k not in seen_keys:
                    seen_keys.add(k)
                    parsed.append(obj)
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


def _clean_model_name(raw: str) -> str:
    val = raw.strip()
    val = re.sub(r"\.\s*$", "", val).strip()
    return val


def get_model_sequence(discovered_models: Optional[List[str]] = None) -> List[str]:
    raw = get_setting("model_fallback_sequence", "")
    seq: List[str] = []
    if raw:
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, list):
                seq = [str(x).strip() for x in loaded if str(x).strip()]
        except Exception:
            seq = []

    if not seq:
        seq = list(DEFAULT_FALLBACK_SEQUENCE)

    changed = False
    # Reemplazar placeholder antiguo si existía
    if "Gemini Flash Lite" in seq:
        seq = [s if s != "Gemini Flash Lite" else "Gemini 3.8 Flash (Low)" for s in seq]
        changed = True

    # Asegurar que todos los motores oficiales (Claude Sonnet, Claude Opus, GPT-OSS, etc.) estén en la lista
    for m in DEFAULT_FALLBACK_SEQUENCE + (discovered_models or []):
        if m and m.lower() != "none" and m not in seq:
            seq.append(m)
            changed = True

    # Evitar duplicados preservando el orden
    seen = set()
    deduped = []
    for s in seq:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    if len(deduped) != len(seq):
        seq = deduped
        changed = True

    if changed or not raw:
        set_setting("model_fallback_sequence", json.dumps(seq, ensure_ascii=False))
    return seq


def move_model_in_sequence(model_name: str, direction: str) -> Dict[str, Any]:
    if direction not in ("up", "down"):
        return {"success": False, "error": "Dirección inválida ('up' o 'down')"}

    seq = get_model_sequence()
    if model_name not in seq:
        return {"success": False, "error": f"Motor '{model_name}' no encontrado en la secuencia"}

    idx = seq.index(model_name)
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(seq):
        seq[idx], seq[swap_idx] = seq[swap_idx], seq[idx]
        set_setting("model_fallback_sequence", json.dumps(seq, ensure_ascii=False))

    return {"success": True, "sequence": seq}


def _get_exhausted_map() -> Dict[str, str]:
    raw = get_setting("model_exhausted_until", "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        # Limpiar caducados
        now_utc = datetime.now(timezone.utc)
        cleaned = {}
        for k, v in data.items():
            dt = _parse_iso_utc(v)
            if dt and dt > now_utc:
                cleaned[k] = v
        if len(cleaned) != len(data):
            set_setting("model_exhausted_until", json.dumps(cleaned, ensure_ascii=False))
        return cleaned
    except Exception:
        return {}


def _mark_model_exhausted(model_name: str, reset_dt_utc: datetime) -> None:
    ex_map = _get_exhausted_map()
    ex_map[model_name] = reset_dt_utc.isoformat()
    set_setting("model_exhausted_until", json.dumps(ex_map, ensure_ascii=False))


def _clear_model_exhausted(model_name: str) -> None:
    ex_map = _get_exhausted_map()
    if model_name in ex_map:
        del ex_map[model_name]
        set_setting("model_exhausted_until", json.dumps(ex_map, ensure_ascii=False))


def clear_model_exhausted(model_name: str) -> None:
    """Función pública para restablecer o desbloquear manualmente la cuota de un motor."""
    _clear_model_exhausted(model_name)


def mark_model_exhausted_hours(model_name: str, hours: int = QUOTA_WINDOW_HOURS) -> None:
    _mark_model_exhausted(model_name, datetime.now(timezone.utc) + timedelta(hours=hours))


def mark_model_exhausted_from_output(model_name: str, output_text: str, default_hours: int = QUOTA_WINDOW_HOURS) -> datetime:
    """Registra el agotamiento de un motor usando la duración exacta reportada por agy (ej. 89h15m) o el valor por defecto."""
    delta = parse_reset_duration(output_text)
    if delta is None:
        delta = timedelta(hours=default_hours)
    reset_dt = datetime.now(timezone.utc) + delta
    _mark_model_exhausted(model_name, reset_dt)
    return reset_dt


def _compute_all_models_metrics(transcripts: List[str], quota_error_active: bool, forced_active_model: Optional[str] = None) -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    window_start_cutoff = now_utc - timedelta(hours=QUOTA_WINDOW_HOURS)

    active_model = forced_active_model or "Gemini 3.8 Flash (Medium)"
    discovered: List[str] = []
    model_steps: Dict[str, List[datetime]] = {}
    last_response_dt_per_model: Dict[str, datetime] = {}

    # Recorrer del más antiguo al más reciente
    for idx in range(len(transcripts) - 1, -1, -1):
        tpath = transcripts[idx]
        mtime_utc = datetime.fromtimestamp(os.path.getmtime(tpath), tz=timezone.utc)
        if idx > 0 and mtime_utc < window_start_cutoff:
            continue

        entries = _read_jsonl_lines(tpath, max_bytes=450000)
        current_conv_model = active_model
        for e in entries:
            if e.get("type") == "USER_INPUT":
                content = e.get("content", "")
                m = re.search(
                    r"changed setting `Model Selection` from (.*?) to ([^\n]+?)(?:\.\s+No need|\.$|$)",
                    content
                )
                if m:
                    prev_m = _clean_model_name(m.group(1))
                    next_m = _clean_model_name(m.group(2))
                    if prev_m and prev_m.lower() != "none":
                        discovered.append(prev_m)
                    if next_m and next_m.lower() != "none":
                        discovered.append(next_m)
                        current_conv_model = next_m
                        if idx == 0 and not forced_active_model:
                            active_model = next_m

            if e.get("type") == "PLANNER_RESPONSE":
                dt = _parse_iso_utc(e.get("created_at", ""))
                if dt and dt >= window_start_cutoff:
                    model_steps.setdefault(current_conv_model, []).append(dt)
                    if current_conv_model not in last_response_dt_per_model or dt > last_response_dt_per_model[current_conv_model]:
                        last_response_dt_per_model[current_conv_model] = dt

    if forced_active_model:
        active_model = forced_active_model

    if active_model not in discovered:
        discovered.append(active_model)

    sequence = get_model_sequence(discovered)
    exhausted_map = _get_exhausted_map()

    # Si hubo error 429 real en el último turno del modelo activo, registrarlo agotado
    if quota_error_active:
        ts_list = sorted(model_steps.get(active_model, []))
        reset_dt = (ts_list[0] + timedelta(hours=QUOTA_WINDOW_HOURS)) if ts_list else (now_utc + timedelta(hours=QUOTA_WINDOW_HOURS))
        _mark_model_exhausted(active_model, reset_dt)
        exhausted_map = _get_exhausted_map()

    models_status = []
    active_model_info = None
    recommended_fallback = None

    for seq_idx, m_name in enumerate(sequence, 1):
        ts_list = sorted(model_steps.get(m_name, []))
        steps_used = len(ts_list)
        budget = _estimate_budget_for_model(m_name)
        is_exhausted = m_name in exhausted_map

        if is_exhausted:
            remaining_pct = 0
            reset_dt = _parse_iso_utc(exhausted_map[m_name]) or (now_utc + timedelta(hours=QUOTA_WINDOW_HOURS))
        elif steps_used == 0:
            remaining_pct = 100
            reset_dt = None
        else:
            raw_pct = int(round((1.0 - (steps_used / float(budget))) * 100))
            if raw_pct <= 0:
                # Si ha superado el presupuesto empírico pero aún responde sin 429, indicar cuota crítica
                remaining_pct = 3
            else:
                remaining_pct = min(100, max(1, raw_pct))
            reset_dt = ts_list[0] + timedelta(hours=QUOTA_WINDOW_HOURS)

        if remaining_pct < 20 or is_exhausted:
            color = "red"
        elif remaining_pct <= 50:
            color = "orange"
        else:
            color = "green"

        if reset_dt:
            remaining_secs = max(0, int((reset_dt - now_utc).total_seconds()))
            days = remaining_secs // 86400
            hours = (remaining_secs % 86400) // 3600
            mins = (remaining_secs % 3600) // 60
            reset_clock = reset_dt.astimezone().strftime("%H:%M")
            date_str = reset_dt.astimezone().strftime("%d/%m")
            if days > 0:
                reset_text = f"Renueva en {days}d {hours}h ({reset_clock} {date_str})"
            elif hours > 0:
                reset_text = f"Renueva en {hours}h {mins:02d}m ({reset_clock})"
            else:
                reset_text = f"Renueva en {mins}m ({reset_clock})"
        else:
            remaining_secs = 0
            reset_text = "100% libre · Sin espera"

        item = {
            "order": seq_idx,
            "name": m_name,
            "cli_id": get_cli_id_for_model(m_name),
            "tier": _describe_tier_for_model(m_name),
            "is_active": (m_name == active_model),
            "is_exhausted": is_exhausted,
            "steps_used": steps_used,
            "steps_budget": budget,
            "quota_remaining_pct": remaining_pct,
            "quota_color": color,
            "reset_in_seconds": remaining_secs,
            "reset_text": reset_text
        }
        models_status.append(item)

        if m_name == active_model:
            active_model_info = item

        if not is_exhausted and remaining_pct > 0 and m_name != active_model and recommended_fallback is None:
            recommended_fallback = item

    # Si todos los de respaldo estuvieran agotados salvo ninguno, buscar el que antes renueva
    if recommended_fallback is None and models_status:
        candidates = [m for m in models_status if m["name"] != active_model and not m["is_exhausted"]]
        if not candidates:
            candidates = [m for m in models_status if m["name"] != active_model]
        if candidates:
            candidates.sort(key=lambda x: x["reset_in_seconds"])
            recommended_fallback = candidates[0]

    if not active_model_info:
        active_model_info = models_status[0]

    return {
        "active_model": active_model_info["name"],
        "quota_remaining_pct": active_model_info["quota_remaining_pct"],
        "quota_color": active_model_info["quota_color"],
        "steps_used": active_model_info["steps_used"],
        "steps_budget": active_model_info["steps_budget"],
        "reset_in_seconds": active_model_info["reset_in_seconds"],
        "reset_text": active_model_info["reset_text"],
        "models": models_status,
        "recommended_fallback": recommended_fallback
    }


def get_watchdog_status() -> Dict[str, Any]:
    global _last_alerted_quota_key

    runner_model = None
    runner_running = False
    runner_task_id = None
    try:
        from app.services.queue_runner import RUNNER_STATE
        if RUNNER_STATE.get("running"):
            runner_running = True
            runner_model = RUNNER_STATE.get("current_model")
            runner_task_id = RUNNER_STATE.get("current_task_id")
    except Exception:
        pass

    transcripts = _find_recent_transcripts()
    if not transcripts:
        models_info = _compute_all_models_metrics([], False, forced_active_model=runner_model)
        return {
            "active": False,
            "state": "working" if runner_running else "idle",
            "label": f"⚡ Ejecutando Tarea #{runner_task_id} ({runner_model})" if runner_running else "Sin sesión detectada",
            "detail": "No se encontró transcript.jsonl",
            "conversation_id": None,
            "quota_alert": False,
            **models_info
        }

    transcript_path = transcripts[0]
    parts = os.path.normpath(transcript_path).split(os.sep)
    conv_id = parts[-4] if len(parts) >= 4 else "desconocido"

    mtime = os.path.getmtime(transcript_path)
    age_seconds = max(0, int(datetime.now().timestamp() - mtime))
    entries = _read_jsonl_lines(transcript_path, max_bytes=65536)

    if not entries:
        models_info = _compute_all_models_metrics(transcripts, False, forced_active_model=runner_model)
        return {
            "active": True,
            "state": "working" if runner_running else "idle",
            "label": f"⚡ Ejecutando Tarea #{runner_task_id} ({runner_model})" if runner_running else "Esperando órdenes",
            "detail": f"Sesión {conv_id[:8]}...",
            "conversation_id": conv_id,
            "age_seconds": age_seconds,
            "quota_alert": False,
            **models_info
        }

    last_entry = entries[-1]
    step_index = last_entry.get("step_index", 0)
    step_type = last_entry.get("type", "")
    step_status = last_entry.get("status", "")

    # Comprobar si el último error real del sistema es 429 (solo si status == ERROR)
    quota_detected = False
    for entry in reversed(entries[-2:]):
        if entry.get("status") == "ERROR":
            raw_dump = json.dumps(entry, ensure_ascii=False).lower()
            if any(k in raw_dump for k in QUOTA_KEYWORDS):
                quota_detected = True
                break

    models_info = _compute_all_models_metrics(transcripts, quota_detected, forced_active_model=runner_model)

    if quota_detected:
        alert_key = f"{conv_id}:{step_index}"
        fallback = models_info.get("recommended_fallback")
        fallback_msg = (
            f"\n➡️ <b>Siguiente motor disponible en tu secuencia:</b> {fallback['name']} ({fallback['quota_remaining_pct']}%)"
            if fallback else "\n⏳ Todos los motores en enfriamiento temporal."
        )
        if _last_alerted_quota_key != alert_key:
            _last_alerted_quota_key = alert_key
            try:
                send_telegram_message(
                    "⚠️ <b>Watchdog Antigravity: Motor Agotado (429)</b>\n\n"
                    f"🆔 <b>Sesión:</b> <code>{conv_id[:8]}</code>\n"
                    f"🤖 <b>Motor agotado:</b> {models_info['active_model']}\n"
                    f"⏳ <b>Recarga:</b> {models_info['reset_text']}"
                    f"{fallback_msg}\n\n"
                    "💡 Cambia al siguiente motor en Antigravity IDE para seguir avanzando sin parar."
                )
            except Exception:
                pass

        return {
            "active": True,
            "state": "quota_error",
            "label": "⚠️ Cuota del motor actual agotada (429)",
            "detail": f"Cambia a: {fallback['name']}" if fallback else "Esperando renovación de cuota",
            "conversation_id": conv_id,
            "step_index": step_index,
            "age_seconds": age_seconds,
            "quota_alert": True,
            **models_info
        }

    if runner_running:
        label = f"⚡ Trabajando #{runner_task_id} ({runner_model})"
        state = "working"
    elif age_seconds <= 25 and (step_status in ("IN_PROGRESS", "RUNNING") or step_type == "USER_INPUT"):
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
        "detail": f"Sesión {conv_id[:8]} · {models_info['active_model']} ({models_info['steps_used']}/{models_info['steps_budget']} pasos 5h)",
        "conversation_id": conv_id,
        "step_index": step_index,
        "age_seconds": age_seconds,
        "quota_alert": False,
        **models_info
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
