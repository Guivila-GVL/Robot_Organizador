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

        with urllib.request.urlopen("http://127.0.0.1:8002/static/js/app.js") as resp:
            js = resp.read().decode("utf-8")
            self.assertIn("openDecompositionModal", js)
            self.assertIn("submitDecompositionCreate", js)
            self.assertIn("openDecomposeModalForTask", js)
            self.assertIn("analyzeDecompositionInClient", js)


if __name__ == "__main__":
    unittest.main()
