import os
import sys
import sqlite3
import unittest
import urllib.request
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.database import get_db_connection, init_db
from app.services.execution_queue import launch_task, pause_task
from app.services.watchdog_service import build_agent_prompt_for_task
from app.services.queue_runner import _build_headless_prompt
from app.services.project_scanner import smart_breakdown_task, _build_atomic_task

SERVER_URL = "http://127.0.0.1:8002"

class TestTaskValidationStructure(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_01_database_has_validation_column(self):
        """Verifica que la tabla tasks cuenta con la columna 'validation'."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row["name"] for row in cursor.fetchall()]
        conn.close()
        self.assertIn("validation", columns, "La columna 'validation' debe existir en la tabla tasks")

    def test_02_task_creation_with_validation_field(self):
        """Verifica la creación de tarea con los 3 campos clave: título, prompt/descripción y validación."""
        conn = get_db_connection()
        cursor = conn.cursor()
        test_title = "Tarea de Prueba Validación Estructurada"
        test_prompt = "Crear función de exportación y enlazar con endpoint REST"
        test_validation = "Ejecutar pytest tests/test_export.py y verificar HTTP 200 en /api/export"

        cursor.execute("""
            INSERT INTO tasks (
                project_id, title, description, validation, priority, status,
                milestone_type, milestone_target, milestone_description,
                order_index, created_at
            ) VALUES (?, ?, ?, ?, 'alta', 'pending', 'command_exit_0', 'pytest tests/test_export.py', ?, 999, datetime('now'))
        """, ("gestion_proyectos", test_title, test_prompt, test_validation, test_validation))
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Verificar lectura directa
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row["title"], test_title)
        self.assertEqual(row["description"], test_prompt)
        self.assertEqual(row["validation"], test_validation)

        # Cleanup
        conn = get_db_connection()
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

    def test_03_launch_task_with_editable_fields(self):
        """Verifica que launch_task permite editar título, prompt y validación antes de subir a ejecución."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (
                project_id, title, description, validation, priority, status,
                order_index, created_at
            ) VALUES (?, ?, ?, ?, 'media', 'pending', 998, datetime('now'))
        """, ("gestion_proyectos", "Título inicial borrador", "Prompt borrador", "Validación borrador"))
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Lanzar la tarea editando los campos (como lo hace el modal antes de subir a ejecución)
        new_title = "Título Definitivo Revisado"
        new_prompt = "Prompt refinado con instrucciones técnicas completas"
        new_validation = "Comprobar que el archivo resultante no está vacío y devuelve código 0"

        res = launch_task(
            task_id=task_id,
            title=new_title,
            description=new_prompt,
            validation=new_validation
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "in_progress")
        self.assertEqual(res["title"], new_title)
        self.assertEqual(res["description"], new_prompt)
        self.assertEqual(res["validation"], new_validation)

        # Verificar en base de datos
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()

        self.assertEqual(row["title"], new_title)
        self.assertEqual(row["description"], new_prompt)
        self.assertEqual(row["validation"], new_validation)
        self.assertEqual(row["status"], "in_progress")

        # Cleanup
        conn = get_db_connection()
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.execute("DELETE FROM comments WHERE task_id = ?", (task_id,))
        conn.commit()
        conn.close()

    def test_04_agent_prompts_include_explicit_validation(self):
        """Verifica que build_agent_prompt_for_task y _build_headless_prompt separan título, prompt y validación."""
        task_data = {
            "id": 9999,
            "project_name": "Robot de Gestión",
            "folder_name": "2026_Proyecto_RobotOrganizador",
            "folder_path": BASE_DIR,
            "title": "Verificar estructura universal",
            "description": "Implementar campo aparte de validación",
            "validation": "Ejecutar test_task_validation_structure.py con éxito",
            "milestone_description": "Ejecutar test_task_validation_structure.py con éxito",
            "milestone_type": "command_exit_0",
            "milestone_target": "python -m unittest tests/test_task_validation_structure.py",
            "priority": "alta"
        }

        headless_prompt = _build_headless_prompt(task_data)
        self.assertIn("Título: Verificar estructura universal", headless_prompt)
        self.assertIn("Descripción / Prompt: Implementar campo aparte de validación", headless_prompt)
        self.assertIn("Validación (Cómo se va a validar):", headless_prompt)
        self.assertIn("Ejecutar test_task_validation_structure.py con éxito", headless_prompt)

    def test_05_api_get_tasks_includes_validation(self):
        """Verifica que el endpoint GET /api/projects/{project_id}/tasks responde con el campo 'validation' en cada tarea."""
        try:
            req = urllib.request.Request(f"{SERVER_URL}/api/projects/gestion_proyectos/tasks")
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                tasks = json.loads(resp.read().decode("utf-8"))
                self.assertIsInstance(tasks, list)
                self.assertGreater(len(tasks), 0)
                task170 = next((t for t in tasks if t["id"] == 170), None)
                self.assertIsNotNone(task170, "La tarea 170 debe estar en la lista de tareas")
                self.assertIn("validation", task170)
                self.assertIn("title", task170)
                self.assertIn("description", task170)
                self.assertTrue(len(task170["validation"]) > 0)
        except urllib.error.URLError as e:
            self.skipTest(f"Servidor FastAPI en {SERVER_URL} no disponible: {e}")

    def test_06_smart_breakdown_includes_validation(self):
        """Verifica que la descomposición inteligente con IA genera el campo 'validation'."""
        res = smart_breakdown_task("Crear backup diario de la base de datos y verificar que se genera en /backups")
        self.assertIn("title", res)
        self.assertIn("description", res)
        self.assertIn("validation", res)
        self.assertTrue(len(res["validation"]) > 0)

    def test_07_index_html_has_launch_modal_and_validation_fields(self):
        """Verifica que index.html contiene el modal de preparación de lanzamiento con título, prompt y validación."""
        html_path = os.path.join(BASE_DIR, "app", "templates", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('id="launchModal"', html)
        self.assertIn('id="launchTaskTitle"', html)
        self.assertIn('id="launchTaskPrompt"', html)
        self.assertIn('id="launchTaskValidation"', html)
        self.assertIn('id="btnConfirmLaunch"', html)
        self.assertIn('id="formValidation"', html)

    def test_08_app_js_has_launch_modal_logic(self):
        """Verifica que app.js contiene la lógica de preparación de lanzamiento editable y validación."""
        js_path = os.path.join(BASE_DIR, "app", "static", "js", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        self.assertIn("openLaunchModal", js)
        self.assertIn("confirmLaunchTask", js)
        self.assertIn("launchTaskValidation", js)
        self.assertIn("formValidation", js)
        self.assertIn("🧪 Validación", js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
