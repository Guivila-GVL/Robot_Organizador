import os
import sys
import sqlite3
import unittest
import urllib.request
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.project_scanner import analyze_task_decomposition, smart_breakdown_task, _build_atomic_task
from app.database import get_db_connection, DB_PATH


class TestTaskDecomposition(unittest.TestCase):

    def test_atomic_task_builder(self):
        res = _build_atomic_task("Crear exportador de facturas en PDF")
        self.assertTrue(res["title"] != "")
        self.assertIn(res["milestone_type"], ["manual", "file_exists"])
        self.assertTrue("exportador de facturas" in res["title"].lower() or "facturas" in res["title"].lower())

    def test_single_task_not_complex(self):
        prompt = "Cambiar color del botón de inicio"
        analysis = analyze_task_decomposition(prompt)
        self.assertFalse(analysis["is_complex"])
        self.assertEqual(len(analysis["subtasks"]), 1)
        self.assertTrue("botón" in analysis["subtasks"][0]["title"].lower() or "color" in analysis["subtasks"][0]["title"].lower())

    def test_numbered_task_decomposition(self):
        prompt = "1. Configurar base de datos SQLite. 2. Implementar endpoints en FastAPI. 3. Validar con pruebas unitarias."
        analysis = analyze_task_decomposition(prompt)
        self.assertTrue(analysis["is_complex"])
        self.assertGreaterEqual(len(analysis["subtasks"]), 3)
        titles = [s["title"].lower() for s in analysis["subtasks"]]
        self.assertTrue(any("sqlite" in t or "base de datos" in t for t in titles))
        self.assertTrue(any("fastapi" in t or "endpoints" in t for t in titles))
        self.assertTrue(any("pruebas" in t or "validar" in t for t in titles))

    def test_connectors_task_decomposition(self):
        prompt = "Crear la tabla de usuarios en SQLite, luego implementar la autenticación JWT y finalmente añadir el formulario de login"
        analysis = analyze_task_decomposition(prompt)
        self.assertTrue(analysis["is_complex"])
        self.assertGreaterEqual(len(analysis["subtasks"]), 3)
        for st in analysis["subtasks"]:
            self.assertTrue(st["title"] != "")
            self.assertTrue(st["description"] != "")
            self.assertIn(st["priority"], ["baja", "media", "alta", "urgente"])

    def test_explicit_split_request(self):
        prompt = "Quiero dividir en subtareas el desarrollo del sistema de alertas push"
        analysis = analyze_task_decomposition(prompt)
        self.assertTrue(analysis["is_complex"])
        self.assertGreaterEqual(len(analysis["subtasks"]), 2)

    def test_force_split_phases(self):
        prompt = "Sistema integral de facturación electrónica"
        analysis = analyze_task_decomposition(prompt, force_split_phases=True)
        self.assertTrue(analysis["is_complex"])
        self.assertEqual(len(analysis["subtasks"]), 3)
        self.assertIn("planificación", analysis["subtasks"][0]["title"].lower())
        self.assertIn("desarrollo", analysis["subtasks"][1]["title"].lower())
        self.assertIn("validación", analysis["subtasks"][2]["title"].lower())

    def test_database_subtask_columns(self):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("PRAGMA table_info(tasks)")
        columns = [r["name"] for r in c.fetchall()]
        conn.close()
        self.assertIn("parent_task_id", columns)
        self.assertIn("is_subtask", columns)

    def test_database_subtask_insertion_and_linking(self):
        conn = get_db_connection()
        c = conn.cursor()
        now = "2026-11-11T19:30:00"

        # Insert a dummy parent task
        c.execute("""
            INSERT INTO tasks (project_id, title, description, priority, status, created_at)
            VALUES ('test_project', 'Tarea Madre Test', 'Tarea grande para desglosar', 'alta', 'pending', ?)
        """, (now,))
        parent_id = c.lastrowid

        # Insert 2 subtasks linked to parent
        c.execute("""
            INSERT INTO tasks (project_id, title, description, priority, status, parent_task_id, is_subtask, created_at)
            VALUES ('test_project', 'Subtarea 1', 'Primera parte', 'alta', 'pending', ?, 1, ?)
        """, (parent_id, now))
        sub1_id = c.lastrowid

        c.execute("""
            INSERT INTO tasks (project_id, title, description, priority, status, parent_task_id, is_subtask, created_at)
            VALUES ('test_project', 'Subtarea 2', 'Segunda parte', 'media', 'pending', ?, 1, ?)
        """, (parent_id, now))
        sub2_id = c.lastrowid

        # Verify query
        c.execute("SELECT * FROM tasks WHERE parent_task_id = ?", (parent_id,))
        subtasks = c.fetchall()
        self.assertEqual(len(subtasks), 2)
        for st in subtasks:
            self.assertEqual(st["is_subtask"], 1)
            self.assertEqual(st["parent_task_id"], parent_id)

        # Cleanup test data
        c.execute("DELETE FROM tasks WHERE id IN (?, ?, ?)", (parent_id, sub1_id, sub2_id))
        conn.commit()
        conn.close()

    def test_frontend_modal_and_js_elements_served(self):
        with urllib.request.urlopen("http://127.0.0.1:8002/") as resp:
            html = resp.read().decode("utf-8")
            self.assertIn('id="decompositionModal"', html)
            self.assertIn('id="decompSubtasksList"', html)
            self.assertIn('id="btnDecompCreateSubtasks"', html)
            self.assertIn('id="btnDecompSingleTask"', html)
            self.assertIn('id="btnModalDecompose"', html)

        with urllib.request.urlopen("http://127.0.0.1:8002/static/js/app.js") as resp:
            js = resp.read().decode("utf-8")
            self.assertIn("openDecompositionModal", js)
            self.assertIn("submitDecompositionCreate", js)
            self.assertIn("openDecomposeModalForTask", js)
            self.assertIn("analyzeDecompositionInClient", js)
            self.assertIn("executeSingleSmartCreate", js)
            # Ensure createSmartTask delegates directly to executeSingleSmartCreate without proposing modal decomposition
            self.assertIn("await executeSingleSmartCreate(prompt);", js)

    def test_smart_create_endpoint_creates_single_task(self):
        # Test that smart-create creates exactly one single task
        payload = json.dumps({
            "project_id": "gestion_proyectos",
            "prompt": "1. Crear endpoint A. 2. Implementar servicio B. 3. Validar con tests."
        }).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8002/api/tasks/smart-create", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            new_id = data.get("task_id")
            self.assertIsNotNone(new_id)

        # Verify in DB it is a single atomic task, not subtask
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE id = ?", (new_id,))
        task = c.fetchone()
        self.assertIsNotNone(task)
        self.assertEqual(task["is_subtask"], 0)
        self.assertIsNone(task["parent_task_id"])

        # Clean up
        c.execute("DELETE FROM tasks WHERE id = ?", (new_id,))
        conn.commit()
        conn.close()

    def test_decompose_existing_task_api(self):
        # 1. Create a parent task
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO tasks (project_id, title, description, priority, status, created_at)
            VALUES ('gestion_proyectos', 'Tarea Compleja Para Desglosar', 'Descripción amplia', 'alta', 'pending', '2026-11-12T19:00:00')
        """)
        parent_id = c.lastrowid
        conn.commit()
        conn.close()

        # 2. Call analyze-breakdown endpoint for this task
        req_an = urllib.request.Request(f"http://127.0.0.1:8002/api/tasks/{parent_id}/analyze-breakdown", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_an) as resp:
            an_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(an_data.get("task_id"), parent_id)
            self.assertGreaterEqual(len(an_data.get("subtasks", [])), 1)

        # 3. Call decompose endpoint
        decompose_payload = json.dumps({
            "project_id": "gestion_proyectos",
            "parent_task_id": parent_id,
            "original_prompt": "Tarea Compleja Para Desglosar",
            "archive_parent": True,
            "subtasks": [
                {"title": "Subtarea Fase 1", "description": "Fase inicial", "priority": "alta", "milestone_type": "manual", "milestone_description": "Validar fase 1"},
                {"title": "Subtarea Fase 2", "description": "Fase secundaria", "priority": "media", "milestone_type": "manual", "milestone_description": "Validar fase 2"}
            ]
        }).encode("utf-8")
        req_dec = urllib.request.Request("http://127.0.0.1:8002/api/tasks/decompose", data=decompose_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_dec) as resp:
            dec_data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(dec_data.get("success"))
            self.assertEqual(dec_data.get("created_count"), 2)
            sub_ids = dec_data.get("task_ids")

        # 4. Verify parent is completed/archived and subtasks are linked
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE id = ?", (parent_id,))
        p = c.fetchone()
        self.assertEqual(p["status"], "completed")
        self.assertIn("Desglosada en 2 subtareas", p["current_step"])

        c.execute("SELECT * FROM tasks WHERE parent_task_id = ?", (parent_id,))
        subs = c.fetchall()
        self.assertEqual(len(subs), 2)
        for st in subs:
            self.assertEqual(st["is_subtask"], 1)
            self.assertEqual(st["parent_task_id"], parent_id)

        # Cleanup
        all_ids = [parent_id] + list(sub_ids)
        c.execute(f"DELETE FROM tasks WHERE id IN ({','.join('?' for _ in all_ids)})", all_ids)
        conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main()
