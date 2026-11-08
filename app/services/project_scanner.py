import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any
from app.database import get_db_connection

BASE_PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

DEFAULT_PROTOCOL_ITEMS = [
    {
        "item_key": "docs",
        "title": "Documentación en /docs",
        "description": "El cambio y las decisiones de diseño quedan explicados en la carpeta docs/ del proyecto.",
        "order_index": 1
    },
    {
        "item_key": "onenote",
        "title": "Registro en OneNote / Bitácora",
        "description": "Se ha actualizado la página de seguimiento en OneNote con el progreso realizado.",
        "order_index": 2
    },
    {
        "item_key": "git",
        "title": "Snapshot / Commit en Git",
        "description": "El repositorio tiene guardado el estado limpio de este cambio.",
        "order_index": 3
    },
    {
        "item_key": "skills",
        "title": "Patrones de Skills aplicados",
        "description": "Se han consultado y respetado los estándares de 0000_Utilidades/01_Skills.",
        "order_index": 4
    },
    {
        "item_key": "validation",
        "title": "Verificación Técnica Superada",
        "description": "El archivo, script o servidor responde exactamente como se esperaba.",
        "order_index": 5
    }
]

DEFAULT_PROJECTS = [
    {
        "id": "gestion_proyectos",
        "name": "Robot de Gestión de Proyectos",
        "folder_name": "2026_Proyecto_RobotOrganizador",
        "category": "Orquestación General",
        "icon": "🤖",
        "color": "#8b5cf6",
        "port": 8002,
        "url": "http://localhost:8002",
        "order_index": 0,
        "description": "Centro de Mando, Gestión de Tareas Multi-Proyecto, Protocolos y Notificaciones Telegram",
        "tasks": [
            {
                "title": "Desplegar Interfaz Web y Servidor FastAPI",
                "description": "Servidor en puerto 8002 con panel visual moderno para planificación y control de tareas.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "http_200",
                "milestone_target": "http://127.0.0.1:8002",
                "milestone_description": "El servidor responde 200 OK y carga el dashboard interactivo.",
                "milestone_result": "Servidor desplegado y operativo en puerto 8002 con arquitectura SQLite y endpoints REST."
            },
            {
                "title": "Protocolo de Cierre Estándar por Tarea",
                "description": "Checklist de verificación post-tarea: Documentación en /docs, OneNote, Git, Skills y Validación.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Panel de protocolo estándar visible en cada proyecto y en el modal de cierre.",
                "milestone_result": "Protocolo estándar integrado en la cabecera y en el envío a Telegram."
            },
            {
                "title": "Asistente Rápido de Tareas por Lenguaje Natural",
                "description": "Creación de tareas en 1 sola frase o dictado de voz sin formularios pesados.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Permitir introducir una idea rápida y desglosarla automáticamente con IA.",
                "milestone_result": "Entrada rápida inteligente activa en la interfaz."
            },
            {
                "title": "Integrar Notificaciones con Foto a Telegram",
                "description": "Configuración del bot @Bot2_Video_bot para reportar cada check completado con imagen y comentario.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Recepción confirmada del mensaje de prueba con foto en el móvil.",
                "milestone_result": "Bot token y chat ID validados; entrega de prueba exitosa (Message ID 16 y 17)."
            },
            {
                "title": "Monitor de Puertos y Lanzador Unificado",
                "description": "Detección en tiempo real de servicios activos (8000, 8001, 8002, 3000, 5678) y botón 'Abrir Todo'.",
                "priority": "media",
                "status": "completed",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Ver todos los servicios encendidos en pestañas de Chrome con un solo clic.",
                "milestone_result": "Lanzador Abrir_Todos_Los_Servicios.bat y botón en dock funcionando."
            },
            {
                "title": "Watchdog de Transcripción y Detección de Cuota Gemini",
                "description": "Monitorizar transcript.jsonl para pausar si Gemini agota cuota (429) y avanzar automáticamente.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "http_200",
                "milestone_target": "http://127.0.0.1:8002/api/watchdog/status",
                "milestone_description": "Bucle autónomo que detecta estado en transcript.jsonl, avisa a Telegram ante error 429 y genera prompts por tarea.",
                "milestone_result": "Servicio watchdog_service.py activo, endpoint /api/watchdog/status en vivo y botón Copiar Prompt en cada tarea."
            },
            {
                "title": "Sistema de Validación Técnica y Carpeta /validacion por Proyecto",
                "description": "Crear y abrir automáticamente la carpeta /validacion y el informe de estado y tests al pulsar en Validación Técnica.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "file_exists",
                "milestone_target": "validacion/ESTADO_VALIDACION.txt",
                "milestone_description": "Al pulsar Validación Técnica se abre la carpeta de validación y el informe actualizado con tests y puertos del proyecto.",
                "milestone_result": "Carpeta /validacion creada y reporte ESTADO_VALIDACION.txt generado y abierto en editor y explorador."
            },
            {
                "title": "Organizar y Documentar Skills y Herramientas Globales",
                "description": "Inventario centralizado de Skills, Servidores MCP, Herramientas Globales y APIs compartidas en 0000_Utilidades/01_Skills y 04_Claves_Subcripciones_APIs con hoja de resumen descriptiva (00_INDICE_SKILLS_Y_PATRONES.txt).",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "file_exists",
                "milestone_target": "D:\\OneDrive\\04_Desarrollo_proyectos\\0000_Utilidades\\01_Skills\\00_INDICE_SKILLS_Y_PATRONES.txt",
                "milestone_description": "Al pulsar Patrones de Skills se abre la carpeta de skills y la hoja de resumen descriptiva de todas las herramientas.",
                "milestone_result": "Catálogo exhaustivo creado en 00_INDICE_SKILLS_Y_PATRONES.txt y README.md; botón de Skills abre carpeta y resumen técnico."
            },
            {
                "title": "Protocolo Automatizado de Cierre de Tareas (Docs, OneNote, Git, Skills)",
                "description": "Al completar cualquier tarea de cualquier proyecto, se ejecuta automáticamente el protocolo de cierre: 1) Registro en docs/REGISTRO_HITOS.md, 2) Sincronización en OneNote (Resumen y Actividades), 3) Commit y Push a GitHub, 4) Revisión de Skills y 5) Alerta a Telegram.",
                "priority": "alta",
                "status": "in_progress",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Comprobación de extremo a extremo del flujo automatizado de cierre general en una tarea.",
                "milestone_result": ""
            }
        ]
    },
    {
        "id": "videos",
        "name": "VideoStudio AI",
        "folder_name": "2026_Proyecto_Videos",
        "category": "Producción Audiovisual",
        "icon": "🎬",
        "color": "#ec4899",
        "port": 8001,
        "url": "http://localhost:8001",
        "order_index": 1,
        "description": "Generación de Vídeos Cortos Narrativos a partir de Libros y Capítulos Literarios",
        "tasks": [
            {
                "title": "Verificar Servidor VideoStudio en Puerto 8001",
                "description": "Comprobar que FastAPI, la base de datos de libros/capítulos y las rutas de vídeo responden correctamente.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "http_200",
                "milestone_target": "http://127.0.0.1:8001",
                "milestone_description": "La página principal carga con el visor de proyectos de libros y generación de escenas.",
                "milestone_result": "Servidor 8001 activo y validado mediante navegador."
            },
            {
                "title": "Alineación de Flujo Telegram para Aprobaciones Humanas",
                "description": "Integrar webhook n8n para enviar por Telegram los clips generados antes del ensamblado final.",
                "priority": "alta",
                "status": "in_progress",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Recepción de botón 'Aprobar' o 'Regenerar escena' en Telegram.",
                "milestone_result": ""
            },
            {
                "title": "Banco de Consistencia de Personajes (--cref / LoRA)",
                "description": "Crear y catalogar hojas de referencia de personajes principales para mantener coherencia en cada capítulo.",
                "priority": "media",
                "status": "pending",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Imágenes de referencia guardadas y accesibles por el generador de prompts.",
                "milestone_result": ""
            }
        ]
    },
    {
        "id": "comentarista",
        "name": "Comentarista X",
        "folder_name": "2026_Proyecto_Comentarista",
        "category": "Redes & Contenido",
        "icon": "✍️",
        "color": "#38bdf8",
        "port": 8000,
        "url": "http://localhost:8000",
        "order_index": 2,
        "description": "Asistente Editorial para X con Generación de Hilos e Integración de Gráficos Grafana",
        "tasks": [
            {
                "title": "Verificar Lanzador y Servidor Local en Puerto 8000",
                "description": "Ejecutar iniciar_comentarista.bat y comprobar respuesta en http://127.0.0.1:8000.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "http_200",
                "milestone_target": "http://127.0.0.1:8000",
                "milestone_description": "El asistente editorial carga con la plantilla de tweets e integración de métricas.",
                "milestone_result": "Servidor en puerto 8000 activo y auto-arranque integrado en el hub de servicios."
            },
            {
                "title": "Validar Conexión con Grafana Renderer (8081)",
                "description": "Comprobar captura automática de paneles de energía para adjuntar imágenes a los comentarios.",
                "priority": "alta",
                "status": "pending",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Descarga de captura PNG del panel de precio horario de Grafana.",
                "milestone_result": ""
            }
        ]
    },
    {
        "id": "energia_graficos",
        "name": "Energía & Gráficos ESIOS",
        "folder_name": "2026_Proyecto_Energia_Graficos",
        "category": "Datos & Automatización",
        "icon": "⚡",
        "color": "#f59e0b",
        "port": 3000,
        "url": "http://localhost:3000",
        "order_index": 3,
        "description": "Series Temporales del Mercado Eléctrico, Ingesta ESIOS, TimescaleDB y Dashboards",
        "tasks": [
            {
                "title": "Verificar Contenedores Docker (TimescaleDB, Grafana, n8n)",
                "description": "Confirmar que la base de datos PostgreSQL/TimescaleDB en el puerto 5432 y Grafana en el 3000 están sanos.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "http_200",
                "milestone_target": "http://127.0.0.1:3000",
                "milestone_description": "Acceso al login o dashboard de Grafana confirmado.",
                "milestone_result": "Docker activo: n8n-python-local, grafana-local, timescaledb-db y grafana-renderer funcionando."
            },
            {
                "title": "Comprobar Actualizador Diario Maestro ESIOS",
                "description": "Verificar ejecución del script de ingesta diaria de curvas de precio y demanda en TimescaleDB.",
                "priority": "alta",
                "status": "in_progress",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Última fecha en base de datos coincide con hoy.",
                "milestone_result": ""
            }
        ]
    },
    {
        "id": "certificado_humano",
        "name": "Certificado Humano",
        "folder_name": "2026_Proyecto_Certificado_Humano",
        "category": "Plataforma Web",
        "icon": "🏅",
        "color": "#10b981",
        "port": 3001,
        "url": "https://human-certified.vercel.app/",
        "order_index": 4,
        "description": "Plataforma de Certificación y Auditoría de Contenido Generado por IA",
        "tasks": [
            {
                "title": "Auditoría de Esquema Prisma y Migraciones",
                "description": "Comprobar compatibilidad entre base de datos de desarrollo (SQLite/Timescale) y producción Vercel.",
                "priority": "media",
                "status": "pending",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Migraciones de Prisma ejecutadas sin inconsistencias.",
                "milestone_result": ""
            },
            {
                "title": "Verificar Despliegue en Vercel",
                "description": "Comprobar salud y rutas de https://human-certified.vercel.app/.",
                "priority": "alta",
                "status": "completed",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Página pública accesible y operativa.",
                "milestone_result": "Despliegue verificado en producción."
            }
        ]
    },
    {
        "id": "remoto",
        "name": "Proyecto Remoto",
        "folder_name": "2026_Proyecto_Remoto",
        "category": "Infraestructura & Conectividad",
        "icon": "🌐",
        "color": "#06b6d4",
        "port": None,
        "url": None,
        "order_index": 5,
        "description": "Control Remoto del Entorno desde Tablet y Smartphone (Tailscale, RDP, SSH, Telegram)",
        "tasks": [
            {
                "title": "Instalar y Enlazar Red Tailscale",
                "description": "Configurar Tailscale en el PC anfitrión para acceder a Grafana, n8n y apps web desde el móvil.",
                "priority": "alta",
                "status": "in_progress",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Dispositivos conectados en la red privada de Tailscale.",
                "milestone_result": ""
            },
            {
                "title": "Activar Servidor de Escritorio Remoto RDP",
                "description": "Ejecutar activar_escritorio_remoto.bat para permitir conexión fluida desde tablet con teclado.",
                "priority": "media",
                "status": "pending",
                "milestone_type": "manual",
                "milestone_target": "",
                "milestone_description": "Acceso por RDP validado desde la red local o Tailscale.",
                "milestone_result": ""
            }
        ]
    }
]

def scan_and_seed_projects(force_reset: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    # Clean old robot_organizador id if present and replace with gestion_proyectos
    cursor.execute("SELECT id FROM projects WHERE id = 'robot_organizador'")
    old_proj = cursor.fetchone()
    if old_proj:
        cursor.execute("UPDATE projects SET id = 'gestion_proyectos', name = 'Robot de Gestión de Proyectos', category = 'Orquestación General', order_index = 0 WHERE id = 'robot_organizador'")
        cursor.execute("UPDATE tasks SET project_id = 'gestion_proyectos' WHERE project_id = 'robot_organizador'")

    for p in DEFAULT_PROJECTS:
        folder_path = os.path.join(BASE_PROJECTS_DIR, p["folder_name"])
        
        cursor.execute("SELECT id FROM projects WHERE id = ?", (p["id"],))
        existing_project = cursor.fetchone()

        if not existing_project:
            cursor.execute("""
            INSERT INTO projects (id, name, folder_name, folder_path, category, icon, color, port, url, description, order_index, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"],
                p["name"],
                p["folder_name"],
                folder_path,
                p["category"],
                p["icon"],
                p["color"],
                p["port"],
                p["url"],
                p["description"],
                p["order_index"],
                now,
                now
            ))
        else:
            # Update name, icon, order_index
            cursor.execute("""
            UPDATE projects SET name = ?, icon = ?, color = ?, order_index = ?, description = ? WHERE id = ?
            """, (p["name"], p["icon"], p["color"], p["order_index"], p["description"], p["id"]))

        # Seed protocol items for project
        cursor.execute("SELECT COUNT(*) as count FROM project_protocols WHERE project_id = ?", (p["id"],))
        proto_count = cursor.fetchone()["count"]
        if proto_count == 0:
            for item in DEFAULT_PROTOCOL_ITEMS:
                cursor.execute("""
                INSERT INTO project_protocols (project_id, item_key, title, description, is_enabled, order_index)
                VALUES (?, ?, ?, ?, 1, ?)
                """, (p["id"], item["item_key"], item["title"], item["description"], item["order_index"]))

        # Deduplicate existing tasks by (project_id, title), keeping the best status
        cursor.execute("""
            DELETE FROM tasks
            WHERE project_id = ?
              AND id NOT IN (
                  SELECT id FROM (
                      SELECT id,
                             ROW_NUMBER() OVER (
                                 PARTITION BY project_id, LOWER(TRIM(title))
                                 ORDER BY CASE status
                                     WHEN 'completed' THEN 1
                                     WHEN 'in_progress' THEN 2
                                     ELSE 3
                                 END ASC, id DESC
                             ) as rn
                      FROM tasks
                      WHERE project_id = ?
                  ) WHERE rn = 1
              )
        """, (p["id"], p["id"]))

        if force_reset:
            cursor.execute("DELETE FROM tasks WHERE project_id = ?", (p["id"],))

        for idx, t in enumerate(p["tasks"]):
            cursor.execute(
                "SELECT id, status FROM tasks WHERE project_id = ? AND LOWER(TRIM(title)) = LOWER(TRIM(?))",
                (p["id"], t["title"])
            )
            existing_task = cursor.fetchone()
            if not existing_task:
                cursor.execute("""
                INSERT INTO tasks (
                    project_id, title, description, priority, status,
                    milestone_type, milestone_target, milestone_description,
                    milestone_result, order_index, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p["id"],
                    t["title"],
                    t["description"],
                    t["priority"],
                    t["status"],
                    t["milestone_type"],
                    t["milestone_target"],
                    t["milestone_description"],
                    t["milestone_result"],
                    idx,
                    now
                ))
            else:
                cursor.execute(
                    "UPDATE tasks SET order_index = ? WHERE id = ?",
                    (idx, existing_task["id"])
                )

    conn.commit()
    conn.close()
    return {"success": True, "message": "Proyectos, protocolos y tareas actualizados con éxito"}

def smart_breakdown_task(prompt: str) -> Dict[str, Any]:
    """
    Desglosa una frase o idea en lenguaje natural en una tarea estructurada con
    título, descripción, criterio de validación concreto y prioridad sugerida.
    """
    clean = prompt.strip()
    if not clean:
        return {}

    title = clean.capitalize()
    description = f"Implementación solicitada: {clean}."
    milestone_desc = f"Verificar que {clean.lower()} funciona correctamente y cumple las expectativas."
    priority = "media"
    milestone_type = "manual"
    milestone_target = ""

    # Detección inteligente por palabras clave
    lower = clean.lower()
    if any(k in lower for k in ["urgente", "critico", "error", "bug", "falla"]):
        priority = "urgente"
    elif any(k in lower for k in ["importante", "servidor", "api", "seguridad", "base de datos", "db"]):
        priority = "alta"
    elif any(k in lower for k in ["mejora", "estilo", "color", "icono", "documentar"]):
        priority = "baja"

    if any(k in lower for k in ["servidor", "puerto", "http", "api", "endpoint"]):
        milestone_type = "http_200"
        m = re.search(r"(\d{4})", lower)
        if m:
            milestone_target = f"http://127.0.0.1:{m.group(1)}"
            milestone_desc = f"Servidor responde 200 OK en el puerto {m.group(1)}."

    elif any(k in lower for k in ["archivo", "exportar", "guardar", "script", "generar", "mp4", "json"]):
        milestone_type = "file_exists"
        milestone_desc = f"Comprobar que el archivo resultante existe en disco con contenido válido."

    return {
        "title": title[:80],
        "description": description,
        "priority": priority,
        "milestone_type": milestone_type,
        "milestone_target": milestone_target,
        "milestone_description": milestone_desc
    }
