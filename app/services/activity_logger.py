import os
import threading
from datetime import datetime
from typing import List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACTIVITY_LOG_PATH = os.path.join(BASE_DIR, "robot_activity.log")
MAX_LOG_LINES = 300
_log_lock = threading.Lock()


def log_activity(source: str, message: str) -> str:
    """Registra un evento operativo del Robot Organizador de forma persistente."""
    ts = datetime.now().strftime("%H:%M:%S")
    clean_msg = " ".join(str(message).splitlines()).strip()
    line = f"[{ts}] [{source.upper()}] {clean_msg}"

    with _log_lock:
        try:
            existing: List[str] = []
            if os.path.exists(ACTIVITY_LOG_PATH):
                with open(ACTIVITY_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    existing = [ln.rstrip("\r\n") for ln in f.readlines() if ln.strip()]
            existing.append(line)
            if len(existing) > MAX_LOG_LINES:
                existing = existing[-MAX_LOG_LINES:]
            with open(ACTIVITY_LOG_PATH, "w", encoding="utf-8", errors="replace") as f:
                f.write("\n".join(existing) + "\n")
        except Exception:
            pass

    try:
        print(line, flush=True)
    except Exception:
        pass
    return line


def read_activity_logs(limit: int = 80) -> List[str]:
    """Devuelve las últimas líneas registradas de actividad y progreso del Robot."""
    with _log_lock:
        if not os.path.exists(ACTIVITY_LOG_PATH):
            return []
        try:
            with open(ACTIVITY_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            return lines[-limit:]
        except Exception:
            return []

