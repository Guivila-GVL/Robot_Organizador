import os
import shutil
import logging
from typing import Optional, List
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime

from app.database import init_db, get_db_connection
from app.services.telegram_service import (
    send_telegram_message,
    send_telegram_photo,
    notify_task_milestone,
    get_setting,
    set_setting
)
from app.services.service_hub import (
    get_services_status,
    open_all_services_in_browser,
    start_local_service,
    open_url_in_system_browser,
    open_project_resource,
    get_combined_service_monitor,
    get_esios_live_status,
    trigger_esios_update,
    _extract_git_remote_url
)
from app.services.project_scanner import scan_and_seed_projects, smart_breakdown_task
from app.services.milestone_checker import check_and_complete_task
from app.services.watchdog_service import get_watchdog_status, build_agent_prompt_for_task, move_model_in_sequence
from app.services.execution_queue import (
    launch_task,
    pause_task,
    update_task_progress,
    get_launched_queue,
    reorder_queue_task
)
from app.services.queue_runner import (
    start_queue_runner,
    stop_queue_runner,
    get_runner_status
)
from app.services.activity_logger import log_activity


class _QuietPollingAccessFilter(logging.Filter):
    """Evita que el polling periódico de la UI sature server_8002.log y tape los logs reales."""
    NOISY_PATHS = (
        "GET /api/services/monitor",
        "GET /api/services ",
        "GET /api/services/esios/status",
        "GET /api/watchdog/status",
        "GET /api/queue ",
        "GET /api/queue/runner-status",
        "GET /api/projects",
        "GET / "
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if " 200" in msg and any(p in msg for p in self.NOISY_PATHS):
            return False
        return True

app = FastAPI(title="Robot de Gestión de Proyectos 2026", version="1.1.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    logging.getLogger("uvicorn.access").addFilter(_QuietPollingAccessFilter())
    init_db()
    scan_and_seed_projects()
    log_activity("ROBOT", "🟢 Servidor Robot Organizador (:8002) iniciado en segundo plano y conectado.")

# Models
class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = ""
    priority: Optional[str] = "media"
    milestone_type: Optional[str] = "manual"
    milestone_target: Optional[str] = ""
    milestone_description: Optional[str] = ""

class SmartTaskCreate(BaseModel):
    project_id: str
    prompt: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    milestone_type: Optional[str] = None
    milestone_target: Optional[str] = None
    milestone_description: Optional[str] = None
    milestone_result: Optional[str] = None

class CommentCreate(BaseModel):
    text: str
    author: Optional[str] = "Usuario"

class CheckRequest(BaseModel):
    comment: Optional[str] = ""
    force_status: Optional[str] = None
    image_url: Optional[str] = None
    protocols_verified: Optional[List[str]] = []

class ProgressUpdate(BaseModel):
    progress_pct: Optional[int] = None
    current_step: Optional[str] = None
    note: Optional[str] = None
    author: Optional[str] = "Agente"

class ModelMoveRequest(BaseModel):
    model_name: str
    direction: str

class SettingsUpdate(BaseModel):
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    n8n_webhook_url: Optional[str] = None
    notify_telegram_enabled: Optional[str] = None
    notify_via_n8n: Optional[str] = None

@app.middleware("http")
async def disable_browser_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "v": int(datetime.now().timestamp())
    })

@app.get("/api/projects")
async def get_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*,
            COUNT(t.id) as total_tasks,
            SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        GROUP BY p.id
        ORDER BY p.order_index ASC, p.id ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    projects = []
    for r in rows:
        total = r["total_tasks"]
        completed = r["completed_tasks"] or 0
        pct = int((completed / total * 100)) if total > 0 else 0
        projects.append({
            "id": r["id"],
            "name": r["name"],
            "folder_name": r["folder_name"],
            "folder_path": r["folder_path"],
            "category": r["category"],
            "icon": r["icon"],
            "color": r["color"],
            "port": r["port"],
            "url": r["url"],
            "description": r["description"],
            "onenote_url": r["onenote_url"] if "onenote_url" in r.keys() else None,
            "git_url": _extract_git_remote_url(r["folder_path"]),
            "total_tasks": total,
            "completed_tasks": completed,
            "progress_percent": pct
        })
    return projects

@app.post("/api/projects/rescan")
async def rescan_projects():
    result = scan_and_seed_projects(force_reset=False)
    return result

@app.post("/api/projects/{project_id}/open-resource/{resource_key}")
async def open_project_resource_endpoint(project_id: str, resource_key: str, open_browser: bool = True):
    return open_project_resource(project_id, resource_key, open_browser=open_browser)

@app.post("/api/projects/{project_id}/sync-onenote")
async def sync_onenote_endpoint(project_id: str):
    from app.services.task_protocol import sync_onenote_project
    res = sync_onenote_project(project_id)
    return res

@app.get("/api/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM tasks
        WHERE project_id = ?
        ORDER BY
            CASE status WHEN 'in_progress' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END ASC,
            CASE WHEN status = 'completed' THEN COALESCE(completed_at, created_at) ELSE '' END DESC,
            CASE WHEN status = 'in_progress' THEN COALESCE(queue_order, 9999) ELSE 0 END ASC,
            created_at DESC,
            id DESC
    """, (project_id,))
    task_rows = cursor.fetchall()

    tasks = []
    for tr in task_rows:
        t_id = tr["id"]
        cursor.execute("SELECT * FROM comments WHERE task_id = ? ORDER BY id ASC", (t_id,))
        c_rows = cursor.fetchall()
        comments = [dict(c) for c in c_rows]
        
        t_dict = dict(tr)
        t_dict["comments"] = comments
        tasks.append(t_dict)

    conn.close()
    return tasks

@app.post("/api/tasks")
async def create_task(task_data: TaskCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("SELECT COALESCE(MAX(order_index), 0) + 1 as next_order FROM tasks WHERE project_id = ?", (task_data.project_id,))
    next_order = cursor.fetchone()["next_order"]

    cursor.execute("""
        INSERT INTO tasks (
            project_id, title, description, priority, status,
            milestone_type, milestone_target, milestone_description,
            order_index, created_at
        ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
    """, (
        task_data.project_id,
        task_data.title,
        task_data.description,
        task_data.priority,
        task_data.milestone_type,
        task_data.milestone_target,
        task_data.milestone_description,
        next_order,
        now
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "task_id": new_id}

@app.post("/api/tasks/smart-create")
async def smart_create_task_endpoint(req: SmartTaskCreate):
    structured = smart_breakdown_task(req.prompt)
    if not structured:
        raise HTTPException(status_code=400, detail="La descripción no puede estar vacía")
    task_obj = TaskCreate(
        project_id=req.project_id,
        title=structured["title"],
        description=structured["description"],
        priority=structured["priority"],
        milestone_type=structured["milestone_type"],
        milestone_target=structured["milestone_target"],
        milestone_description=structured["milestone_description"]
    )
    return await create_task(task_obj)

@app.get("/api/projects/{project_id}/protocols")
async def get_project_protocols(project_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_protocols WHERE project_id = ? ORDER BY order_index ASC", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.put("/api/tasks/{task_id}")
async def update_task(task_id: int, updates: TaskUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    fields = []
    values = []
    for k, v in updates.dict(exclude_unset=True).items():
        fields.append(f"{k} = ?")
        values.append(v)

    if not fields:
        conn.close()
        return {"success": True, "message": "Nada que actualizar"}

    values.append(task_id)
    cursor.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return {"success": True}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    cursor.execute("DELETE FROM comments WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"success": True}

@app.post("/api/tasks/{task_id}/check")
async def run_task_check(task_id: int, req: CheckRequest):
    final_comment = req.comment or ""
    if req.protocols_verified:
        proto_text = "\n\n📋 <b>Protocolo Verificado:</b>\n" + "\n".join([f"  ✅ {p}" for p in req.protocols_verified])
        final_comment += proto_text

    result = check_and_complete_task(
        task_id=task_id,
        comment=final_comment,
        image_path=req.image_url,
        force_status=req.force_status
    )
    return result

@app.post("/api/tasks/{task_id}/comments")
async def add_task_comment(task_id: int, comment: CommentCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO comments (task_id, author, text, created_at)
        VALUES (?, ?, ?, ?)
    """, (task_id, comment.author or "Usuario", comment.text, now))
    conn.commit()
    conn.close()
    return {"success": True}

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = os.path.join(UPLOADS_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"success": True, "file_url": f"/uploads/{filename}", "file_path": file_path}

@app.get("/api/services")
def get_services():
    return get_services_status()

@app.post("/api/services/open-all")
def open_all_services():
    return open_all_services_in_browser()

@app.get("/api/services/monitor")
def services_monitor_endpoint():
    return get_combined_service_monitor()

@app.get("/api/services/esios/status")
def esios_status_endpoint():
    return get_esios_live_status()

@app.post("/api/services/esios/start")
def esios_start_endpoint():
    return trigger_esios_update()

@app.post("/api/services/{service_id}/start")
def start_service_endpoint(service_id: str, open_browser: bool = True):
    res = start_local_service(service_id, wait_ready=True)
    if res.get("success") and open_browser and res.get("url"):
        open_url_in_system_browser(res["url"])
    return res

@app.get("/api/watchdog/status")
def watchdog_status_endpoint():
    return get_watchdog_status()

@app.post("/api/watchdog/models/move")
async def move_watchdog_model_endpoint(req: ModelMoveRequest):
    res = move_model_in_sequence(req.model_name, req.direction)
    if res.get("success"):
        res["status"] = get_watchdog_status()
    return res

@app.get("/api/tasks/{task_id}/prompt")
async def get_task_agent_prompt(task_id: int):
    return build_agent_prompt_for_task(task_id)

@app.post("/api/tasks/{task_id}/launch")
async def launch_task_endpoint(task_id: int):
    return launch_task(task_id)

@app.post("/api/tasks/{task_id}/pause")
async def pause_task_endpoint(task_id: int):
    return pause_task(task_id)

@app.patch("/api/tasks/{task_id}/progress")
async def update_progress_endpoint(task_id: int, req: ProgressUpdate):
    return update_task_progress(
        task_id=task_id,
        progress_pct=req.progress_pct,
        current_step=req.current_step,
        note=req.note,
        author=req.author or "Agente"
    )

@app.get("/api/queue")
async def get_queue_endpoint(project_id: Optional[str] = None):
    return get_launched_queue(project_id)

@app.post("/api/queue/{task_id}/move/{direction}")
async def move_queue_task_endpoint(task_id: int, direction: str):
    return reorder_queue_task(task_id, direction)

@app.post("/api/queue/run")
async def start_queue_runner_endpoint():
    return start_queue_runner()

@app.post("/api/queue/stop")
async def stop_queue_runner_endpoint():
    return stop_queue_runner()

@app.get("/api/queue/runner-status")
async def runner_status_endpoint():
    return get_runner_status()

@app.get("/api/settings")
async def get_all_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    for k, v in settings.dict(exclude_unset=True).items():
        if v is not None:
            set_setting(k, str(v))
    return {"success": True}

@app.post("/api/telegram/test")
async def test_telegram():
    sample_text = (
        "🤖 <b>Robot Organizador: Prueba de Conexión Exitosa</b>\n\n"
        "✅ El bot @Bot2_Video_bot está correctamente enlazado con tu panel de control.\n"
        "📱 A partir de ahora recibirás aquí los checks completados de cada proyecto con sus comentarios y capturas de pantalla.\n\n"
        f"⏱ <i>Hora: {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}</i>"
    )
    res = send_telegram_message(sample_text)
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8002, reload=True)
