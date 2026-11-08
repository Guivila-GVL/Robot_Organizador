# Robot Organizador 2026 🤖📋📱

Centro de Mando, Gestión de Tareas Multi-Proyecto y Notificaciones Automáticas a Telegram para el entorno de desarrollo local.

---

## 🎯 Objetivo

Permitir planificar, organizar y ejecutar tareas e hitos secuenciales de todos los proyectos (`Videos`, `Comentarista`, `Certificado Humano`, `Energía & Gráficos`, `Remoto`), verificar su cumplimiento y **enviar automáticamente una notificación a Telegram con el resumen y la captura o imagen del resultado** sin necesidad de estar sentado frente al ordenador.

---

## 🌐 Ecosistema de Servicios Locales

| Servicio | Puerto | Descripción | Acceso |
|---|---|---|---|
| **Robot Organizador** | `:8002` | Centro de Mando, Backlog, Hitos y Telegram | `http://localhost:8002` |
| **VideoStudio AI** | `:8001` | Producción de Vídeos Cortos Narrativos | `http://localhost:8001` |
| **Comentarista X** | `:8000` | Asistente Editorial con Grafana e IA | `http://localhost:8000` |
| **n8n Automation** | `:5678` | Motor de Automatización y Webhooks | `http://localhost:5678` |
| **Grafana** | `:3000` | Dashboards de Series Temporales de Energía | `http://localhost:3000` |
| **TimescaleDB** | `:5432` | Base de Datos PostgreSQL / Series Temporales | `localhost:5432` |
| **Certificado Humano** | Producción | Plataforma de Auditoría Técnica de IA | `https://human-certified.vercel.app/` |

---

## 🚀 Inicio Rápido

1. **Iniciar el Robot Organizador:**
   Haz doble clic en `Iniciar_RobotOrganizador.bat` (o en la raíz de `04_Desarrollo_proyectos`).
   Se abrirá en `http://localhost:8002`.

2. **Abrir todos los servicios en pestañas de Chrome:**
   Haz clic en el botón superior **"🌐 Abrir Todo"** dentro de la web o ejecuta `Abrir_Todos_Los_Servicios.bat`.

3. **Probar Telegram:**
   Haz clic en el botón superior **"📱 Probar Telegram"**. Recibirás un mensaje de confirmación del bot `@Bot2_Video_bot` en tu móvil.

4. **Completar un Hito con Imagen:**
   En cualquier tarea, pulsa **"✅ Completar & Telegram"**, escribe el comentario del resultado, adjunta una foto o captura si lo deseas y pulsa **"🚀 Completar & Enviar Telegram"**.

---

## 📁 Estructura del Proyecto

```
2026_Proyecto_RobotOrganizador/
├── app/
│   ├── main.py                  # Servidor FastAPI y API REST (Puerto 8002)
│   ├── database.py              # Motor SQLite (robot_organizador.db)
│   ├── services/
│   │   ├── telegram_service.py  # Conexión directa y por webhook a Telegram
│   │   ├── service_hub.py       # Monitor de puertos activos y lanzador
│   │   ├── project_scanner.py   # Descubrimiento automático de proyectos
│   │   └── milestone_checker.py # Validador automático de criterios de hito
│   ├── templates/
│   │   └── index.html           # Interfaz web interactiva
│   ├── static/
│   │   ├── css/style.css        # Sistema de diseño dark mode con glassmorphism
│   │   └── js/app.js            # Controlador reactivo en Vanilla JS
│   └── uploads/                 # Capturas e imágenes de resultados enviadas
├── n8n/
│   └── flujo_robot_telegram.json # Flujo para importar en n8n
├── Iniciar_RobotOrganizador.bat  # Lanzador local
└── README.md                    # Documentación
```
